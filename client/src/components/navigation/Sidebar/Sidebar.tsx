import './Sidebar.css'

function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Primary">
      <span className="sidebar__title">MENU</span>
      <div className="sidebar__content">
        <div className="sidebar__card sidebar__card--bookmarks">
          <button type="button" className="sidebar__link">
            My Bookmarks
          </button>
          <span className="sidebar__divider" aria-hidden="true"></span>
          <button type="button" className="sidebar__link">
            My Notes
          </button>
        </div>
        <div className="sidebar__card sidebar__card--main">
          <div className="sidebar__menu">
            <button type="button" className="sidebar__link">
              Get Started
            </button>
            <span className="sidebar__divider" aria-hidden="true"></span>
            <button type="button" className="sidebar__link">
              Internships
            </button>
            <span className="sidebar__divider" aria-hidden="true"></span>
            <button type="button" className="sidebar__link">
              Placements
            </button>
            <span className="sidebar__divider" aria-hidden="true"></span>
            <button type="button" className="sidebar__link">
              Resume Repository
            </button>
            <span className="sidebar__divider" aria-hidden="true"></span>
            <button type="button" className="sidebar__link">
              About Reach
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
