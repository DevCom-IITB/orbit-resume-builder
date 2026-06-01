import './ResumesList.css'
import type { ResumeItem } from '../../../data/resumes'

const headerItems = ['File', 'Pages', 'Type', 'Date']

const FolderIcon = () => (
  <svg
    className="resumes__icon"
    width="30"
    height="30"
    viewBox="0 0 30 30"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M3.75 7.5V21C3.75 22.4001 3.75 23.0997 4.02248 23.6345C4.26217 24.1049 4.64434 24.4881 5.11475 24.7278C5.649 25 6.34874 25 7.74613 25H22.2539C23.6513 25 24.35 25 24.8842 24.7278C25.3546 24.4881 25.7381 24.1051 25.9778 23.6347C26.2503 23.1 26.2503 22.3999 26.2503 20.9998L26.2503 11.4997C26.2503 10.0996 26.2503 9.39953 25.9778 8.86475C25.7381 8.39434 25.3549 8.01217 24.8845 7.77248C24.3497 7.5 23.6501 7.5 22.25 7.5H15M3.75 7.5H15M3.75 7.5C3.75 6.11929 4.86929 5 6.25 5H10.8431C11.4546 5 11.7611 5 12.0488 5.06908C12.3039 5.13032 12.5473 5.23158 12.771 5.36865C13.0232 5.52321 13.2398 5.73977 13.6719 6.17188L15 7.5"
      stroke="#050316"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const FileIcon = () => (
  <svg
    className="resumes__icon"
    width="30"
    height="30"
    viewBox="0 0 30 30"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M11.25 21.25H18.75M11.25 17.5H18.75M16.2505 3.75109C16.1311 3.75 15.9967 3.75 15.8434 3.75H10.2502C8.85011 3.75 8.14953 3.75 7.61475 4.02249C7.14434 4.26217 6.76217 4.64434 6.52248 5.11475C6.25 5.64953 6.25 6.35011 6.25 7.75024V22.2502C6.25 23.6504 6.25 24.3501 6.52248 24.8849C6.76217 25.3553 7.14434 25.7381 7.61475 25.9778C8.14901 26.25 8.84875 26.25 10.2462 26.25L19.7539 26.25C21.1513 26.25 21.85 26.25 22.3842 25.9778C22.8546 25.7381 23.2381 25.3553 23.4778 24.8849C23.75 24.3506 23.75 23.6519 23.75 22.2545V11.6571C23.75 11.5038 23.7499 11.3694 23.7488 11.25M16.2505 3.75109C16.6073 3.75434 16.8322 3.76758 17.0477 3.81934C17.3028 3.88058 17.5473 3.98158 17.771 4.11865C18.0232 4.27321 18.2398 4.48977 18.6719 4.92188L22.5787 8.82873C23.0111 9.26111 23.2261 9.4767 23.3807 9.72899C23.5178 9.95267 23.6192 10.1966 23.6804 10.4517C23.7322 10.6672 23.7455 10.8932 23.7488 11.25M16.2505 3.75109L16.25 7.25026C16.25 8.65039 16.25 9.35019 16.5225 9.88497C16.7622 10.3554 17.1443 10.7381 17.6147 10.9778C18.149 11.25 18.8488 11.25 20.2461 11.25H23.7488"
      stroke="#050316"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const StarIcon = () => (
  <svg
    className="resumes__icon"
    width="27"
    height="26"
    viewBox="0 0 27 26"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M1.20239 10.5537C0.81083 10.1915 1.02353 9.53693 1.55315 9.47414L9.05762 8.58402C9.27347 8.55843 9.46096 8.42288 9.552 8.2255L12.7173 1.36327C12.9407 0.878973 13.6292 0.87888 13.8525 1.36317L17.0178 8.22536C17.1089 8.42274 17.2951 8.55865 17.511 8.58424L25.0159 9.47414C25.5455 9.53693 25.7576 10.1917 25.366 10.5538L19.8184 15.6851C19.6588 15.8327 19.5878 16.0523 19.6301 16.2655L21.1025 23.6776C21.2064 24.2007 20.6497 24.606 20.1843 24.3455L13.5901 20.6535C13.4005 20.5473 13.17 20.5478 12.9804 20.6539L6.38549 24.3446C5.92011 24.6051 5.36237 24.2007 5.46631 23.6776L6.93887 16.266C6.98123 16.0528 6.91036 15.8326 6.75078 15.685L1.20239 10.5537Z"
      fill="#FFD000"
      stroke="#050316"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const DownloadIcon = () => (
  <svg
    className="resumes__action-icon"
    width="30"
    height="30"
    viewBox="0 0 30 30"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M7.5 26.25H22.5M15 3.75V21.25M8.75 15L15 21.25L21.25 15"
      stroke="#2645F2"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const MenuDotsIcon = () => (
  <svg
    className="resumes__action-icon resumes__action-icon--menu"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M17 12C17 12.5523 17.4477 13 18 13C18.5523 13 19 12.5523 19 12C19 11.4477 18.5523 11 18 11C17.4477 11 17 11.4477 17 12Z"
      stroke="#050316"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M11 12C11 12.5523 11.4477 13 12 13C12.5523 13 13 12.5523 13 12C13 11.4477 12.5523 11 12 11C11.4477 11 11 11.4477 11 12Z"
      stroke="#050316"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M5 12C5 12.5523 5.44772 13 6 13C6.55228 13 7 12.5523 7 12C7 11.4477 6.55228 11 6 11C5.44772 11 5 11.4477 5 12Z"
      stroke="#050316"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

function ResumesList({ items }: { items: ResumeItem[] }) {
  const sortedItems = [...items].sort(
    (a, b) => Number(Boolean(b.starred)) - Number(Boolean(a.starred))
  )

  return (
    <section className="resumes" aria-label="My resumes">
      <header className="resumes__header">
        <h2 className="resumes__title">My Resumes</h2>
        <button className="resumes__button" type="button">
          <svg
            className="resumes__button-icon"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <circle
              cx="12"
              cy="12"
              r="10"
              fill="none"
              stroke="#ffffff"
              strokeWidth="1.5"
            />
            <line
              x1="12"
              y1="7"
              x2="12"
              y2="17"
              stroke="#ffffff"
              strokeWidth="1.5"
            />
            <line
              x1="7"
              y1="12"
              x2="17"
              y2="12"
              stroke="#ffffff"
              strokeWidth="1.5"
            />
          </svg>
          Create a resume
        </button>
      </header>

      <div className="resumes__table">
        <div className="resumes__row-wrap resumes__row-wrap--head">
          <div className="resumes__row resumes__row--head">
            <div className="resumes__cell resumes__cell--file">
              <FolderIcon />
              {headerItems[0]}
            </div>
            <div className="resumes__cell resumes__cell--pages">
              {headerItems[1]}
            </div>
            <div className="resumes__cell resumes__cell--type">
              {headerItems[2]}
            </div>
            <div className="resumes__cell resumes__cell--date">
              {headerItems[3]}
            </div>
          </div>
          <div
            className="resumes__actions resumes__actions--spacer"
            aria-hidden="true"
          ></div>
        </div>

        {sortedItems.map((item) => (
          <div className="resumes__row-wrap" key={item.id}>
            <div className="resumes__row">
              <div className="resumes__cell resumes__cell--file">
                {item.starred ? <StarIcon /> : <FileIcon />}
                {item.name}
              </div>
              <div className="resumes__cell resumes__cell--pages">
                {item.pages} Page
              </div>
              <div className="resumes__cell resumes__cell--type">
                {item.type}
              </div>
              <div className="resumes__cell resumes__cell--date">
                {item.updatedAt}
              </div>
            </div>
            <div className="resumes__actions">
              <DownloadIcon />
              <MenuDotsIcon />
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default ResumesList
