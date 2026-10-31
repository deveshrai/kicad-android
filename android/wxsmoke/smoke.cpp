// wxQt-on-Android smoke test: a frame with a menu bar, a text control and an input panel
// that reports every mouse, wheel and key event it receives.  Used to validate the
// wxWidgets/Qt stack and keyboard+mouse handling on the emulator before KiCad runs.

#include <wx/wx.h>

#include <deque>


class INPUT_PANEL : public wxPanel
{
public:
    explicit INPUT_PANEL( wxWindow* aParent ) :
            wxPanel( aParent, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxWANTS_CHARS )
    {
        SetBackgroundStyle( wxBG_STYLE_PAINT );

        Bind( wxEVT_PAINT, &INPUT_PANEL::onPaint, this );

        for( wxEventType t : { wxEVT_LEFT_DOWN, wxEVT_LEFT_UP, wxEVT_RIGHT_DOWN, wxEVT_RIGHT_UP,
                               wxEVT_MIDDLE_DOWN, wxEVT_MIDDLE_UP, wxEVT_MOTION,
                               wxEVT_MOUSEWHEEL, wxEVT_LEFT_DCLICK } )
        {
            Bind( wxEventTypeTag<wxMouseEvent>( t ), &INPUT_PANEL::onMouse, this );
        }

        Bind( wxEVT_KEY_DOWN, &INPUT_PANEL::onKey, this );
        Bind( wxEVT_CHAR, &INPUT_PANEL::onChar, this );
    }

private:
    void log( const wxString& aLine )
    {
        // Mirror to logcat so tests can assert on events without screenshots
        fprintf( stderr, "WXSMOKE %s\n", aLine.utf8_str().data() );
        m_lines.push_front( aLine );

        if( m_lines.size() > 30 )
            m_lines.pop_back();

        Refresh();
    }

    void onMouse( wxMouseEvent& aEvent )
    {
        m_cursor = aEvent.GetPosition();

        if( aEvent.Moving() || aEvent.Dragging() )
        {
            if( aEvent.Dragging() )
                log( wxString::Format( "drag %d,%d", m_cursor.x, m_cursor.y ) );
            else
                Refresh();

            return;
        }

        wxString what = aEvent.LeftDown()     ? "left down"
                        : aEvent.LeftUp()     ? "left up"
                        : aEvent.RightDown()  ? "right down"
                        : aEvent.RightUp()    ? "right up"
                        : aEvent.MiddleDown() ? "middle down"
                        : aEvent.MiddleUp()   ? "middle up"
                        : aEvent.LeftDClick() ? "left dclick"
                        : aEvent.GetEventType() == wxEVT_MOUSEWHEEL
                                ? wxString::Format( "wheel %d", aEvent.GetWheelRotation() )
                                : wxString( "mouse" );

        log( wxString::Format( "%s at %d,%d%s%s", what, m_cursor.x, m_cursor.y,
                               aEvent.ControlDown() ? " +ctrl" : "",
                               aEvent.ShiftDown() ? " +shift" : "" ) );

        if( aEvent.ButtonDown() )
            SetFocus();

        aEvent.Skip();
    }

    void onKey( wxKeyEvent& aEvent )
    {
        log( wxString::Format( "key down code=%d%s%s%s", aEvent.GetKeyCode(),
                               aEvent.ControlDown() ? " +ctrl" : "",
                               aEvent.AltDown() ? " +alt" : "",
                               aEvent.ShiftDown() ? " +shift" : "" ) );
        aEvent.Skip();
    }

    void onChar( wxKeyEvent& aEvent )
    {
        wxChar c = aEvent.GetUnicodeKey();
        log( wxString::Format( "char '%c' (%d)", c ? c : ' ', (int) c ) );
    }

    void onPaint( wxPaintEvent& )
    {
        wxPaintDC dc( this );
        dc.SetBackground( *wxWHITE_BRUSH );
        dc.Clear();

        // Crosshair at the last pointer position
        dc.SetPen( wxPen( *wxRED, 1 ) );
        dc.CrossHair( m_cursor );

        dc.SetTextForeground( *wxBLACK );
        int y = 8;

        for( const wxString& line : m_lines )
        {
            dc.DrawText( line, 8, y );
            y += dc.GetCharHeight() + 2;
        }
    }

    std::deque<wxString> m_lines;
    wxPoint              m_cursor;
};


class SMOKE_FRAME : public wxFrame
{
public:
    SMOKE_FRAME() : wxFrame( nullptr, wxID_ANY, "wxQt smoke test" )
    {
        wxMenu* file = new wxMenu;
        file->Append( wxID_OPEN, "&Open...\tCtrl+O" );
        file->Append( wxID_EXIT, "E&xit\tCtrl+Q" );

        wxMenuBar* bar = new wxMenuBar;
        bar->Append( file, "&File" );
        SetMenuBar( bar );

        auto sizer = new wxBoxSizer( wxVERTICAL );
        sizer->Add( new wxTextCtrl( this, wxID_ANY, "Type here" ), 0, wxEXPAND | wxALL, 4 );
        m_panel = new INPUT_PANEL( this );
        sizer->Add( m_panel, 1, wxEXPAND );
        SetSizer( sizer );

        CreateStatusBar();
        SetStatusText( wxString::Format( "wx %s", wxVERSION_NUM_DOT_STRING ) );

        Bind( wxEVT_MENU, [this]( wxCommandEvent& ) { Close(); }, wxID_EXIT );
        Bind( wxEVT_MENU,
              [this]( wxCommandEvent& )
              {
                  wxFileDialog dlg( this, "Open" );
                  dlg.ShowModal();
              },
              wxID_OPEN );

        fprintf( stderr, "WXSMOKE frame created\n" );
    }

private:
    INPUT_PANEL* m_panel;
};


class SMOKE_APP : public wxApp
{
public:
    bool OnInit() override
    {
        ( new SMOKE_FRAME )->Show();
        return true;
    }
};

wxIMPLEMENT_APP( SMOKE_APP );
