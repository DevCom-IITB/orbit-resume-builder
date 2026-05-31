import './IntroSteps.css'
import introOne from '../../../assets/svg/intro-page-1.svg'
import introTwo from '../../../assets/svg/intro-page-2.svg'
import introThree from '../../../assets/svg/intro-page-3.svg'
import introFour from '../../../assets/svg/intro-page-4.svg'

const steps = [
  {
    src: introOne,
    label: 'Describe Your Experience',
    description:
      'Write about your experience naturally — projects, internships, research, PORs, or achievements.',
  },
  {
    src: introTwo,
    label: 'AI Refines Your Content',
    description:
      'The AI converts your raw description into professional resume-ready content.',
  },
  {
    src: introThree,
    label: 'Edit with Full Flexibility',
    description:
      'Edit the generated content, customize formatting, choose bullet points, and optimize spacing.',
  },
  {
    src: introFour,
    label: 'Generate Resume PDF',
    description:
      'Generate clean LaTeX-based resume PDFs with live preview and smart page fitting.',
  },
]

function IntroSteps() {
  return (
    <section className="intro" aria-label="Resume steps">
      <h2 className="intro__title">My Resumes</h2>
      <div className="intro__steps">
        {steps.map((step, index) => (
          <div className="intro__card" key={step.label}>
            <div className="intro__art">
              <img className="intro__image" src={step.src} alt="" />
            </div>
            <div className="intro__divider" aria-hidden="true">
              <span className="intro__line"></span>
              <span className="intro__badge">{index + 1}</span>
              <span className="intro__line"></span>
            </div>
            <div className="intro__text">
              <span className="intro__label">{step.label}</span>
              <span className="intro__description">{step.description}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="intro__actions">
        <button className="intro__button" type="button">
          <svg
            className="intro__button-icon"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" fill="none" stroke="#ffffff" strokeWidth="1.5" />
            <line x1="12" y1="7" x2="12" y2="17" stroke="#ffffff" strokeWidth="1.5" />
            <line x1="7" y1="12" x2="17" y2="12" stroke="#ffffff" strokeWidth="1.5" />
          </svg>
          Create a resume
        </button>
      </div>
    </section>
  )
}

export default IntroSteps
