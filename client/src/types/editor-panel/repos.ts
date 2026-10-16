export type Repo = {
    id: number,
    name: string,
    language: string,
    selected: boolean
}

export type Project = {
    id: string,
    title: string,
    language: string,
    readme: string,
    generation: boolean
}