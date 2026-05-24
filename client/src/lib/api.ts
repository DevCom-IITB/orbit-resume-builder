import axios from 'axios'

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

/**
 * We create a reusable instance so we don't have to repeat headers, timeouts,
 * or base URLs for every single network call.
 */
export const APIInstance = axios.create({
  // Vite securely pulls the string from your .env file at build time.
  // Fallbacks to localhost if the environment variable is missing.
  // Make sure your .env has: VITE_API_HOST=http://localhost:8000
  baseURL: import.meta.env?.VITE_API_HOST,

  // 5 minute timeout for potentially long AI generation tasks
  timeout: 300000,

  // CRITICAL FOR AUTH: Ensures session cookies/JWTs are sent to your Django backend
  withCredentials: true,

  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// ============================================================================
// SECTION GENERATION API
// ============================================================================

/**
 * Universal function to call the backend for ANY resume section.
 * It dynamically routes to `/generate/<sectiontype>`.
 * * @param sectionName - Must be one of the defined SectionTypes
 * @param rawInputText - The text the user typed into the draft input box
 * @returns The parsed JSON response from the backend
 */
export async function generateSectionData(
  sectionName: SectionType,
  rawInputText: string
) {
  try {
    // Axios handles stringifying the body and parsing the JSON response automatically.
    // We dynamically inject the sectionName directly into the URL path.
    const response = await APIInstance.post(
      `/api/resume-renderer/${sectionName}`,
      {
        input: rawInputText,
      }
    )

    // response.data contains the already-parsed JSON from your backend
    return response.data
  } catch (error) {
    console.error(`[API Error - ${sectionName}]:`, error)
    throw error
  }
}

// ============================================================================
// PDF GENERATION API
// ============================================================================

/**
 * Sends the aggregated resume data to the backend and parses the returned PDF bytes.
 * * @param resumeData - The master JSON object containing all sections
 * @returns A local Blob URL pointing to the generated PDF
 */
export async function generatePdfData(
  resumeData: Record<string, unknown>
): Promise<string> {
  try {
    // We pass a third argument to override specific configurations just for THIS request
    const response = await APIInstance.post(
      '/api/resume-renderer/render/',
      resumeData,
      {
        headers: {
          // Tell the backend we expect the file, not standard JSON
          Accept: 'application/pdf',
        },

        // CRITICAL: Tell Axios to leave the bytes as a raw binary Blob
        responseType: 'blob',
      }
    )

    // Axios automatically extracts the Blob because of the responseType above
    const pdfBlob = response.data

    // Convert the binary Blob into a secure, temporary local URL for the iframe
    return URL.createObjectURL(pdfBlob)
  } catch (error) {
    console.error('[API Error - PDF Generation]:', error)
    throw error
  }
}
