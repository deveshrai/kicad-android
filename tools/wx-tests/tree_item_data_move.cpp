// Moving a wxTreeCtrl item's client data to another item, as KiCad's rule editor does on a drag:
// SetItemData(newItem, data); SetItemData(oldItem, nullptr); then use newItem's data.
#include <wx/wx.h>
#include <wx/treectrl.h>

struct DATA : wxTreeItemData { int id; explicit DATA( int i ) : id( i ) {} };

class APP : public wxApp
{
    bool OnInit() override
    {
        wxFrame*    f = new wxFrame( nullptr, wxID_ANY, "t" );
        wxTreeCtrl* t = new wxTreeCtrl( f );
        wxTreeItemId root = t->AddRoot( "root" );
        wxTreeItemId a = t->AppendItem( root, "a", -1, -1, new DATA( 42 ) );
        wxTreeItemId b = t->AppendItem( root, "b" );

        wxTreeItemData* d = t->GetItemData( a );
        t->SetItemData( b, d );
        t->SetItemData( a, nullptr );
        t->Delete( a );

        DATA* got = dynamic_cast<DATA*>( t->GetItemData( b ) );
        printf( "moved data id = %d (expect 42)\n", got ? got->id : -1 );
        t->Delete( b );   // frees the data once
        printf( "ok\n" );
        f->Destroy();
        return false;
    }
};

wxIMPLEMENT_APP_CONSOLE( APP );
