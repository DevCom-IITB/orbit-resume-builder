import axios from 'axios'
import type { PointDensity } from '../types/editor-panel/pointdensity'
// --- Types ---
export type SectionType =
    | 'scholastic_achievements'
    | 'professional_experience'
    | 'positions_of_responsibility'
    | 'education'
    | 'key_projects'
    | 'courses'
    | 'technical_skills'

// ============================================================================
// AXIOS BASE INSTANCE
// ============================================================================

export const APIInstance = axios.create({
    baseURL: import.meta.env?.VITE_API_HOST,
    timeout: 300000, // 5 minute timeout for LLM generation
    withCredentials: false,
    headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
    },
})

// ============================================================================
// SECTION GENERATION API
// ============================================================================

export async function generateSectionData(
    sectionName: SectionType,
    rawInputText: string,
    density: PointDensity = 'standard',
    fitToLine: boolean = true
    // Added density parameter with a default fallback
) {
    try {
        const response = await APIInstance.post(
            `/api/resume-renderer/${sectionName}/`,
            {
                user_input: rawInputText, // Matches Django's expected key
                density: density, // Sends the slider value to Django
                fit_to_line: fitToLine, // Sends the fit-to-line value to Django
            }
        )

        // Unwraps the Django response to return ONLY the AI-generated array/object
        return response.data.data
    } catch (error) {
        console.error(`[API Error - ${sectionName}]:`, error)
        throw error
    }
}

// ============================================================================
// PDF GENERATION API
// ============================================================================

export interface RenderedResumeResponse {
    pdfUrl: string
    latexCode: string
}

// ============================================================================
// RESUME CRUD API
// ============================================================================

export interface ResumeRecord {
    id: string
    title: string
    resume_type: 'ONE' | 'TWO'
    header_type: 'SHORT' | 'LONG'
    created_at: string
    updated_at: string
}

export interface CreateResumePayload {
    title: string
    resume_type: 'ONE' | 'TWO'
    header_type: 'SHORT' | 'LONG'
}

export async function listResumes(): Promise<ResumeRecord[]> {
    const response = await APIInstance.get('/api/resumes/')
    return response.data.results ?? []
}

export async function createResume(
    payload: CreateResumePayload
): Promise<ResumeRecord> {
    const response = await APIInstance.post('/api/resumes/', payload)
    return response.data
}

export async function generateResumeAssets(
    resumeData: Record<string, unknown>
): Promise<RenderedResumeResponse> {
    try {
        const response = await APIInstance.post(
            '/api/resume-renderer/render/',
            resumeData,
            {
                headers: {
                    Accept: 'application/json',
                },
            }
        )

        const pdfBase64 = response.data?.pdf
        const latexCode = response.data?.latex

        if (typeof pdfBase64 !== 'string') {
            throw new Error('PDF payload missing or invalid')
        }
        if (typeof latexCode !== 'string') {
            throw new Error('LaTeX payload missing or invalid')
        }

        const binaryString = atob(pdfBase64)
        const byteArray = new Uint8Array(binaryString.length)
        for (let i = 0; i < binaryString.length; i += 1) {
            byteArray[i] = binaryString.charCodeAt(i)
        }
        const pdfBlob = new Blob([byteArray], { type: 'application/pdf' })
        const pdfUrl = URL.createObjectURL(pdfBlob)

        return {
            pdfUrl,
            latexCode,
        }
    } catch (error) {
        console.error('[API Error - Resume Asset Generation]:', error)
        throw error
    }
}
