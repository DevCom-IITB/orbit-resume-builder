import { createPortal } from 'react-dom'
import './ProjectModal.css'
interface ProjectModalProps {
    open: boolean
    onClose: () => void
    onGithub: () => void
    onManual: () => void
}

const ProjectModal = ({
    open,
    onClose,
    onGithub,
    onManual,
}: ProjectModalProps) => {
    if (!open) return null

    return createPortal(
        <div className="modal-overlay" onClick={onClose}>
            <div
                className="modal-container"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="project-modal-header">
                    <h2>Add Project</h2>
                    <p>Choose how you would like to add your project.</p>
                </div>

                <div className="project-modal-options">
                    <button className="project-option-card" onClick={onGithub}>
                        <div className="project-option-content">
                            <h3>Import from GitHub</h3>
                            <p>
                                Import repositories directly from your GitHub
                                account.
                            </p>
                        </div>

                        <span className="project-option-arrow">→</span>
                    </button>

                    <button className="project-option-card" onClick={onManual}>
                        <div className="project-option-content">
                            <h3>Create Manually</h3>
                            <p>Enter all project information yourself.</p>
                        </div>

                        <span className="project-option-arrow">→</span>
                    </button>
                </div>
            </div>
        </div>,
        document.body
    )
}

export default ProjectModal
