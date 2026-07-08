import { createPortal } from "react-dom";
import githubLogo from '../../../assets/githubLogo.png';
import './GithubAuthModal.css'

interface GithubAuthModalProps {
    open: boolean
    onClose: (status: string) => void
    authStatus: 'auth' | 'fetch' | 'error' | 'idle'
}

const GithubAuthModal = ({open, onClose, authStatus}: GithubAuthModalProps) => {

    if(!open) return null;
    
    const modalContent = {
        auth: {
            title: "Connecting to GitHub",
            description:
                "Finish signing in from the GitHub popup. This window will close automatically afterwards.",
            loadingText: "Waiting for GitHub...",
        },
        fetch: {
            title: "Authentication Successful",
            description:
                "You're connected! Fetching your repositories.",
            loadingText: "Loading repositories...",
        },
        error: {
            title: "Authentication Failed",
            description:
                "GitHub authentication was cancelled or unsuccessful.",
            loadingText: "Closing...",
        },
    }

    const content = modalContent[authStatus]

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
                    {content.title}
                </h2>

                <p className="github-auth-description">
                    {content.description}
                </p>

                <div className="github-auth-loading">
                    <span className="github-auth-spinner" />

                    <span>
                        {content.loadingText}
                    </span>
                </div>

                <button
                    disabled={authStatus === 'fetch'}
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