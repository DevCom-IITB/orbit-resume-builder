import axios from 'axios'
import type {
    FontOption,
    GetStyleResponse,
    PatchStyleResponse,
    Resume,
    ResumeListItem,
    ResumeSection,
    ResumeTemplate,
    SectionEntry,
    SwitchPlanResponse,
    SwitchTemplateSuccessResponse,
    TemplateSectionManifest,
    VisualTheme,
} from '../types/resume'
import type { Repo } from '../types/editor-panel/repos'

// ============================================================================
// AXIOS BASE INSTANCE
// ============================================================================

export const APIInstance = axios.create({
    baseURL: import.meta.env?.VITE_API_HOST,
    timeout: 300000,
    withCredentials: false,
    headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
    },
})

export const GithubAPIInstance = axios.create({
    baseURL: import.meta.env?.VITE_API_HOST,
    timeout: 300000,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
    },
})

// ============================================================================
// RESPONSE MAPPING HELPERS
// ============================================================================

function mapEntry(raw: any): SectionEntry {
    return {
        id: raw.id,
        order: raw.order,
        rawInput: raw.raw_input,
        content: raw.content,
        generationStatus: raw.generation_status,
    }
}

function mapSection(raw: any): ResumeSection {
    return {
        id: raw.id,
        sectionType: {
            key: raw.section_type.key,
            displayName: raw.section_type.display_name,
            allowMultipleEntries: raw.section_type.allow_multiple_entries,
            entryHintText: raw.section_type.entry_hint_text,
        },
        order: raw.order,
        isVisible: raw.is_visible,
        entries: (raw.entries ?? []).map(mapEntry),
    }
}

function mapResume(raw: any): Resume {
    return {
        id: raw.id,
        title: raw.title,
        template: {
            key: raw.template.key,
            displayName: raw.template.display_name,
            fontDefault: raw.template.font_default,
            accentDefault: raw.template.accent_default,
            lineSpacingDefault: raw.template.line_spacing_default,
            wordSpacingDefault: raw.template.word_spacing_default,
        },
        visualTheme: { key: raw.visual_theme.key, displayName: raw.visual_theme.display_name },
        pages: raw.pages,
        configOverride: raw.config_override ?? {},
        isPinned: raw.is_pinned,
        sections: (raw.sections ?? []).map(mapSection),
        createdAt: raw.created_at,
        updatedAt: raw.updated_at,
    }
}

function mapListItem(raw: any): ResumeListItem {
    return {
        id: raw.id,
        title: raw.title,
        template: { key: raw.template.key, displayName: raw.template.display_name },
        visualTheme: { key: raw.visual_theme.key, displayName: raw.visual_theme.display_name },
        isPinned: raw.is_pinned,
        createdAt: raw.created_at,
        updatedAt: raw.updated_at,
    }
}

function mapTemplate(raw: any): ResumeTemplate {
    return {
        key: raw.key,
        displayName: raw.display_name,
        family: raw.family,
        domain: raw.domain,
        maxPages: raw.max_pages,
        templateConfig: raw.template_config ?? {},
        availableThemes: (raw.available_themes ?? []).map((t: any): VisualTheme => ({
            key: t.key,
            displayName: t.display_name,
            compatibleFamilies: t.compatible_families ?? [],
        })),
        defaultThemeKey: raw.default_theme_key,
        fonts: (raw.fonts ?? []).map((f: any): FontOption => ({
            key: f.key,
            label: f.label,
        })),
        fontDefault: raw.font_default,
        accents: raw.accents ?? [],
        accentDefault: raw.accent_default,
        lineSpacings: raw.line_spacings ?? [],
        lineSpacingDefault: raw.line_spacing_default,
        wordSpacings: raw.word_spacings ?? [],
        wordSpacingDefault: raw.word_spacing_default,
        sections: (raw.sections ?? []).map((s: any): TemplateSectionManifest => ({
            key: s.key,
            displayName: s.display_name,
            isDefault: s.is_default,
            isRequired: s.is_required,
            defaultOrder: s.default_order,
        })),
    }
}

// ============================================================================
// TEMPLATES & THEMES
// ============================================================================

export async function listTemplates(): Promise<ResumeTemplate[]> {
    const res = await APIInstance.get('/api/resumes/templates/')
    return res.data.map(mapTemplate)
}

export async function listThemes(family?: string): Promise<VisualTheme[]> {
    const params = family ? { family } : {}
    const res = await APIInstance.get('/api/resumes/themes/', { params })
    return res.data.map((t: any): VisualTheme => ({
        key: t.key,
        displayName: t.display_name,
        compatibleFamilies: t.compatible_families ?? [],
    }))
}

// ============================================================================
// RESUME CRUD
// ============================================================================

export async function listResumes(): Promise<{ count: number; results: ResumeListItem[] }> {
    const res = await APIInstance.get('/api/resumes/')
    return {
        count: res.data.count ?? 0,
        results: (res.data.results ?? []).map(mapListItem),
    }
}

export async function getResume(id: string): Promise<Resume> {
    const res = await APIInstance.get(`/api/resumes/${id}/`)
    return mapResume(res.data)
}

export interface CreateResumePayload {
    title: string
    templateKey: string
    visualThemeKey: string
    pages?: number
    configOverride?: Record<string, any>
}

export async function createResume(payload: CreateResumePayload): Promise<Resume> {
    const res = await APIInstance.post('/api/resumes/', {
        title: payload.title,
        template_key: payload.templateKey,
        visual_theme_key: payload.visualThemeKey,
        pages: payload.pages ?? 1,
        config_override: payload.configOverride ?? {},
    })
    return mapResume(res.data)
}

export interface PatchResumePayload {
    title?: string
    visualThemeKey?: string
    pages?: number
    configOverride?: Record<string, any>
    isPinned?: boolean
}

export async function patchResume(id: string, payload: PatchResumePayload): Promise<Resume> {
    const body: Record<string, any> = {}
    if (payload.title !== undefined) body.title = payload.title
    if (payload.visualThemeKey !== undefined) body.visual_theme_key = payload.visualThemeKey
    if (payload.pages !== undefined) body.pages = payload.pages
    if (payload.configOverride !== undefined) body.config_override = payload.configOverride
    if (payload.isPinned !== undefined) body.is_pinned = payload.isPinned
    const res = await APIInstance.patch(`/api/resumes/${id}/`, body)
    return mapResume(res.data)
}

export async function deleteResume(id: string): Promise<void> {
    await APIInstance.delete(`/api/resumes/${id}/`)
}

export async function duplicateResume(id: string): Promise<Resume> {
    const res = await APIInstance.post(`/api/resumes/${id}/duplicate/`)
    return mapResume(res.data)
}

// ============================================================================
// SECTIONS
// ============================================================================

export async function addSection(resumeId: string, sectionTypeKey: string): Promise<ResumeSection> {
    const res = await APIInstance.post(`/api/resumes/${resumeId}/sections/`, {
        section_type_key: sectionTypeKey,
    })
    return mapSection(res.data)
}

export async function updateSection(
    resumeId: string,
    sectionId: string,
    payload: { order?: number; isVisible?: boolean }
): Promise<ResumeSection> {
    const body: Record<string, any> = {}
    if (payload.order !== undefined) body.order = payload.order
    if (payload.isVisible !== undefined) body.is_visible = payload.isVisible
    const res = await APIInstance.patch(
        `/api/resumes/${resumeId}/sections/${sectionId}/`,
        body
    )
    return mapSection(res.data)
}

export async function deleteSection(resumeId: string, sectionId: string): Promise<void> {
    await APIInstance.delete(`/api/resumes/${resumeId}/sections/${sectionId}/`)
}

// ============================================================================
// ENTRIES
// ============================================================================

export async function addEntry(
    resumeId: string,
    sectionId: string,
    rawInput = ''
): Promise<SectionEntry> {
    const res = await APIInstance.post(
        `/api/resumes/${resumeId}/sections/${sectionId}/entries/`,
        { raw_input: rawInput }
    )
    return mapEntry(res.data)
}

export async function updateEntry(
    resumeId: string,
    sectionId: string,
    entryId: string,
    payload: { rawInput?: string; content?: any; order?: number }
): Promise<SectionEntry> {
    const body: Record<string, any> = {}
    if (payload.rawInput !== undefined) body.raw_input = payload.rawInput
    if (payload.content !== undefined) body.content = payload.content
    if (payload.order !== undefined) body.order = payload.order
    const res = await APIInstance.patch(
        `/api/resumes/${resumeId}/sections/${sectionId}/entries/${entryId}/`,
        body
    )
    return mapEntry(res.data)
}

export async function deleteEntry(
    resumeId: string,
    sectionId: string,
    entryId: string
): Promise<void> {
    await APIInstance.delete(
        `/api/resumes/${resumeId}/sections/${sectionId}/entries/${entryId}/`
    )
}

// ============================================================================
// GENERATION & RENDERING
// ============================================================================

export async function generateEntry(
    resumeId: string,
    sectionId: string,
    entryId: string
): Promise<SectionEntry> {
    const res = await APIInstance.post(
        `/api/resumes/${resumeId}/sections/${sectionId}/entries/${entryId}/generate/`
    )
    return mapEntry(res.data)
}

export function base64ToPdfBlobUrl(pdfBase64: string): string {
    const binaryString = atob(pdfBase64)
    const byteArray = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
        byteArray[i] = binaryString.charCodeAt(i)
    }
    const pdfBlob = new Blob([byteArray], { type: 'application/pdf' })
    return URL.createObjectURL(pdfBlob)
}

export async function getStyle(resumeId: string): Promise<GetStyleResponse> {
    const res = await APIInstance.get(`/api/resumes/${resumeId}/style/`)
    const styleData = res.data.style || {}
    return {
        style: {
            font: styleData.font,
            accent: styleData.accent,
            lineSpacing: styleData.line_spacing ?? '1.00',
            wordSpacing: styleData.word_spacing ?? '1.00',
            line_spacing: styleData.line_spacing,
            word_spacing: styleData.word_spacing,
        },
        options: {
            fonts: (res.data.options?.fonts ?? []).map((f: any) => ({
                key: f.key,
                label: f.label,
            })),
            fontDefault: res.data.options?.font_default ?? 'lmodern',
            accents: res.data.options?.accents ?? [],
            accentDefault: res.data.options?.accent_default ?? '#4B41C8',
            lineSpacings: res.data.options?.line_spacings ?? [],
            lineSpacingDefault: res.data.options?.line_spacing_default ?? '1.00',
            wordSpacings: res.data.options?.word_spacings ?? [],
            wordSpacingDefault: res.data.options?.word_spacing_default ?? '1.00',
        },
    }
}

export async function patchStyle(
    resumeId: string,
    patch: {
        font?: string
        accent?: string
        lineSpacing?: string
        wordSpacing?: string
        line_spacing?: string
        word_spacing?: string
    },
    signal?: AbortSignal
): Promise<PatchStyleResponse> {
    const body: Record<string, any> = {}
    if (patch.font !== undefined) body.font = patch.font
    if (patch.accent !== undefined) body.accent = patch.accent
    if (patch.lineSpacing !== undefined) body.line_spacing = patch.lineSpacing
    else if (patch.line_spacing !== undefined) body.line_spacing = patch.line_spacing
    if (patch.wordSpacing !== undefined) body.word_spacing = patch.wordSpacing
    else if (patch.word_spacing !== undefined) body.word_spacing = patch.word_spacing

    const res = await APIInstance.patch(`/api/resumes/${resumeId}/style/`, body, { signal })
    const data = res.data
    return {
        changed: data.changed,
        style: {
            font: data.style?.font,
            accent: data.style?.accent,
            lineSpacing: data.style?.line_spacing ?? '1.00',
            wordSpacing: data.style?.word_spacing ?? '1.00',
            line_spacing: data.style?.line_spacing,
            word_spacing: data.style?.word_spacing,
        },
        pdf: data.pdf,
        latex: data.latex,
        pages: data.pages ?? data.page_count,
        pageCount: data.page_count ?? data.pages,
    }
}

export async function switchTemplate(
    resumeId: string,
    payload: { templateKey: string; themeKey?: string; dryRun?: boolean },
    signal?: AbortSignal
): Promise<SwitchPlanResponse | SwitchTemplateSuccessResponse> {
    const body: Record<string, any> = {
        template_key: payload.templateKey,
        dry_run: Boolean(payload.dryRun),
    }
    if (payload.themeKey) {
        body.theme_key = payload.themeKey
    }
    const res = await APIInstance.post(`/api/resumes/${resumeId}/template/`, body, { signal })
    const data = res.data
    if (data.dry_run) {
        return {
            dryRun: true,
            plan: {
                willHide: data.plan?.will_hide ?? [],
                willAddEmpty: data.plan?.will_add_empty ?? [],
                willRestore: data.plan?.will_restore ?? [],
                styleReset: data.plan?.style_reset ?? [],
                unchanged: data.plan?.unchanged ?? [],
            },
        }
    }

    return {
        changed: data.changed,
        template: {
            key: data.template?.key,
            displayName: data.template?.display_name,
        },
        themeKey: data.theme_key,
        sections: (data.sections ?? []).map((s: any) => ({
            key: s.key,
            displayName: s.display_name,
            order: s.order,
            isVisible: s.is_visible,
            hasData: s.has_data,
        })),
        style: {
            font: data.style?.font,
            accent: data.style?.accent,
            lineSpacing: data.style?.line_spacing ?? '1.00',
            wordSpacing: data.style?.word_spacing ?? '1.00',
            line_spacing: data.style?.line_spacing,
            word_spacing: data.style?.word_spacing,
        },
        options: {
            fonts: (data.options?.fonts ?? []).map((f: any) => ({
                key: f.key,
                label: f.label,
            })),
            fontDefault: data.options?.font_default ?? 'lmodern',
            accents: data.options?.accents ?? [],
            accentDefault: data.options?.accent_default ?? '#4B41C8',
            lineSpacings: data.options?.line_spacings ?? [],
            lineSpacingDefault: data.options?.line_spacing_default ?? '1.00',
            wordSpacings: data.options?.word_spacings ?? [],
            wordSpacingDefault: data.options?.word_spacing_default ?? '1.00',
        },
        warnings: data.warnings ?? [],
        pdf: data.pdf,
        latex: data.latex,
        pages: data.pages ?? data.page_count,
        pageCount: data.page_count ?? data.pages,
    }
}

export interface RenderedResumeResponse {
    pdfUrl: string
    latexCode: string
}

export async function renderResume(resumeId: string): Promise<RenderedResumeResponse> {
    const res = await APIInstance.post(`/api/resumes/${resumeId}/render/`)

    const pdfBase64 = res.data?.pdf
    const latexCode = res.data?.latex

    if (typeof pdfBase64 !== 'string') throw new Error('PDF payload missing or invalid')
    if (typeof latexCode !== 'string') throw new Error('LaTeX payload missing or invalid')

    const pdfUrl = base64ToPdfBlobUrl(pdfBase64)
    return { pdfUrl, latexCode }
}

export async function getGithubAuthorizationUrl(redirectTo: string): Promise<string> {
    const res = await APIInstance.get(
        "/api/resume-renderer/github/connect/",
        {
            params: {
                redirect_to: redirectTo,
            },
        }
    )

    return res.data.authorization_url
}

export async function getGithubStatus(): Promise<boolean> {
    const res = await GithubAPIInstance.get(
        "/api/resume-renderer/github/status/"
    )

    return res.data.connected
}

export async function getGithubRepositories() {
    const res = await GithubAPIInstance.get(
        "/api/resume-renderer/github/repositories/"
    )

    return res.data.data
}

export async function importGithubProjects(repositories: Repo[]) {
    const res = await GithubAPIInstance.post(
        "/api/resume-renderer/github/import-projects/",
        {
            repositories,
        }
    )

    return res.data.data
}
