import { createPortal } from "react-dom";
import githubLogo from '../../../assets/githubLogo.png';
import './GithubAuthModal.css'

interface GithubAuthModalProps {
    open: boolean
    onClose: (status: string) => void
}

const GithubAuthModal = ({open, onClose}: GithubAuthModalProps) => {

    if(!open) return null;
    
    return createPortal(
        <div
            className="modal-overlay"
            onClick={() => {
                onClose('authenticated')
            }}
        >
            <div
                className="modal-container github-auth-container"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="github-auth-logo-container">
                    <img
                        src={githubLogo}
                        alt="GitHub"
                        className="github-auth-logo"
                    />
                </div>

                <h2 className="github-auth-title">
                    Connecting to GitHub
                </h2>

                <p className="github-auth-description">
                    Finish signing in from the GitHub popup.
                    This window will close automatically afterwards.
                </p>

                <div className="github-auth-loading">
                    <span className="github-auth-spinner" />

                    <span>
                        Waiting for GitHub...
                    </span>
                </div>

                <button
                    className="github-auth-cancel"
                    onClick={() => {
                        onClose('cancel')
                    }}
                >
                    Cancel
                </button>
            </div>
        </div>,
        document.body
    );
};

export default GithubAuthModal;