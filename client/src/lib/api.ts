import axios from 'axios'
import type {
    Resume,
    ResumeListItem,
    ResumeSection,
    ResumeTemplate,
    SectionEntry,
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
        template: { key: raw.template.key, displayName: raw.template.display_name },
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
    importContent?: string
}

export async function createResume(payload: CreateResumePayload): Promise<Resume> {
    const res = await APIInstance.post('/api/resumes/', {
        title: payload.title,
        template_key: payload.templateKey,
        visual_theme_key: payload.visualThemeKey,
        pages: payload.pages ?? 1,
        config_override: payload.configOverride ?? {},
        import_content: payload.importContent || undefined,
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

export interface LLMGenerationErrorPayload {
    status: number
    error: string
    limitType?: '30_minute' | 'daily'
    message: string
    retryAfter?: number
    resetAt?: string
    blockedUntil?: string
    details?: string
}

export class LLMGenerationError extends Error {
    payload: LLMGenerationErrorPayload
    constructor(payload: LLMGenerationErrorPayload) {
        super(payload.message || 'LLM generation failed')
        this.name = 'LLMGenerationError'
        this.payload = payload
    }
}

export async function generateEntry(
    resumeId: string,
    sectionId: string,
    entryId: string
): Promise<SectionEntry> {
    try {
        const res = await APIInstance.post(
            `/api/resumes/${resumeId}/sections/${sectionId}/entries/${entryId}/generate/`
        )
        return mapEntry(res.data)
    } catch (err: unknown) {
        if (axios.isAxiosError(err) && err.response) {
            const data = (err.response.data as Record<string, unknown>) || {}
            throw new LLMGenerationError({
                status: err.response.status,
                error: (data.error as string) || 'unknown_error',
                limitType: data.limit_type as '30_minute' | 'daily' | undefined,
                message: (data.message as string) || err.message,
                retryAfter: data.retry_after as number | undefined,
                resetAt: data.reset_at as string | undefined,
                blockedUntil: data.blocked_until as string | undefined,
                details: data.details as string | undefined,
            })
        }
        throw err
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

    const binaryString = atob(pdfBase64)
    const byteArray = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
        byteArray[i] = binaryString.charCodeAt(i)
    }
    const pdfBlob = new Blob([byteArray], { type: 'application/pdf' })
    const pdfUrl = URL.createObjectURL(pdfBlob)

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
