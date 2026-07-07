import { createPortal } from "react-dom";
import type { Repo } from "../../../types/editor-panel/repos";
import './GithubModal.css';

interface GithubModalProps {
    open: boolean
    repos: Repo[]
    onClose: () => void
    onRepoToggle: (id: number) => void
    onImport: () => void
    onClear: () => void
}

const GithubModal = ({open, repos, onClose, onRepoToggle, onImport, onClear}: GithubModalProps) => { 
    if(!open) return null;

    const hasSelectedRepos = repos.some(repo => repo.selected);

    return createPortal (
        <div
            className="modal-overlay"
            onClick={onClose}
        >
            <div
                className="modal-container"
                onClick={(e) => e.stopPropagation()}
            >

                <h2 className="github-modal-title">
                    Select Projects to Import
                </h2>

                <p className="github-modal-subtitle">
                    Choose one or more repositories to import into your resume.
                </p>

                <div className="github-repo-list">

                    {repos.map((repo) => (

                        <div
                            key={repo.id}
                            className={`github-repo-card ${repo.selected ? "selected" : ""}`}
                            onClick={() => onRepoToggle(repo.id)}
                        >

                            <div className="github-repo-left">

                                <input
                                    type="checkbox"
                                    checked={repo.selected}
                                    className="github-repo-checkbox"
                                    onClick={(e) => e.stopPropagation()}
                                    onChange={() => onRepoToggle(repo.id)}
                                />
                                <div className="github-repo-content">

                                    <span className="github-repo-name">
                                        {repo.name}
                                    </span>

                                    <span className="github-repo-language">
                                        {repo.language}
                                    </span>

                                </div>

                            </div>

                        </div>

                    ))}

                </div>

                <div className="github-modal-footer">

                    <button
                        className="github-clear-button"
                        disabled={!hasSelectedRepos}
                        onClick={onClear}
                        >
                        Clear All
                    </button>

                    <button
                        className="github-import-button"
                        disabled={!hasSelectedRepos}
                        onClick={onImport}
                    >
                        Import Selected
                    </button>

                </div>

            </div>

        </div>,

        document.body
    );
};

export default GithubModal