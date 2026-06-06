import { useState } from 'react'
import { IntroSteps, ResumesList, Sidebar, TopBar } from '../../components'
import { resumes } from '../../data/resumes'
import ResumePreferencesModal from '../../components/ResumePreferencesModal/ResumePreferencesModal'
import '../App.css'

function Home() {
    const [showModal, setShowModal] = useState(false)

    return (
        <div className="app">
            <TopBar />
            <div className="app__body">
                <Sidebar />
                <div className="app__main">
                    {resumes.length === 0 ? (
                        <IntroSteps />
                    ) : (
                        <ResumesList
                            items={resumes}
                            onStartMaking={() => setShowModal(true)}
                        />
                    )}
                </div>
            </div>

            <ResumePreferencesModal
                isOpen={showModal}
                onClose={() => setShowModal(false)}
                onCreate={() => {
                    setShowModal(false)
                }}
            />
        </div>
    )
}

export default Home
