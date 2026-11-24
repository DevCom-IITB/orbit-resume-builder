import { beforeEach, expect, it, vi } from 'vitest'
import { APIInstance, generateEntry, updateEntry } from './api'

beforeEach(() => vi.restoreAllMocks())

it.each([true, false])(
    'sends fit_to_line in the generation POST body: %s',
    async (enabled) => {
        const post = vi.spyOn(APIInstance, 'post').mockResolvedValue({
            data: { id: 'e', fitting: { status: 'disabled', bullets: [] } },
        })
        const result = await generateEntry('r', 's', 'e', enabled)
        expect(post).toHaveBeenCalledWith(
            '/api/resumes/r/sections/s/entries/e/generate/',
            { fit_to_line: enabled }
        )
        expect(result.fitting?.status).toBe('disabled')
    }
)

it('sends manual content without any fitting option or generation call', async () => {
    const patch = vi
        .spyOn(APIInstance, 'patch')
        .mockResolvedValue({ data: { id: 'e', content_origin: 'manual' } })
    const post = vi.spyOn(APIInstance, 'post')
    const content = [{ bullets: ['  Exact chosen text\n'] }]
    const result = await updateEntry('r', 's', 'e', { content })
    expect(patch).toHaveBeenCalledWith('/api/resumes/r/sections/s/entries/e/', {
        content,
    })
    expect(post).not.toHaveBeenCalled()
    expect(result.contentOrigin).toBe('manual')
})
