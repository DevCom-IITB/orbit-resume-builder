export type ResumeItem = {
  id: string
  name: string
  pages: number
  type: string
  updatedAt: string
  starred?: boolean
}

export const resumes: ResumeItem[] = [
  {
    id: 'resume-1',
    name: 'Software Intern Resume',
    pages: 1,
    type: 'PDF',
    updatedAt: '22/5/2026',
    starred: true,
  },
  {
    id: 'resume-2',
    name: 'Research CV',
    pages: 2,
    type: 'PDF',
    updatedAt: '14/5/2026',
  },
  {
    id: 'resume-3',
    name: 'Placement Profile',
    pages: 1,
    type: 'PDF',
    updatedAt: '02/5/2026',
  },
]
