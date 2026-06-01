import { IntroSteps, ResumesList, Sidebar, TopBar } from '../../components'
import { resumes } from '../../data/resumes'
import '../App.css'

function Home() {
  return (
    <div className="app">
      <TopBar />
      <div className="app__body">
        <Sidebar />
        <div className="app__main">
          {resumes.length === 0 ? (
            <IntroSteps />
          ) : (
            <ResumesList items={resumes} />
          )}
        </div>
      </div>
    </div>
  )
}

export default Home
