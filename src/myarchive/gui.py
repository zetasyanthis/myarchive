
import logging

from gi.repository import Gtk, GLib, GdkPixbuf

from taginator.db.tables import TrackedFile, Tag

# Get the module logger.
logger = logging.getLogger(__name__)


class MainWindow(Gtk.Window):

    def __init__(self, tag_db):
        Gtk.Window.__init__(self, title="Taginator")

        # Configure self.
        self.tag_db = tag_db
        self.set_default_size(960, 540)
        self.set_border_width(1)
        self.connect("delete-event", Gtk.main_quit)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.box)

        self.menubar = MainWindowMenuBar(
            name="main_menu",
            parent=self,
            visible=True)
        self.box.pack_start(self.menubar, expand=False, fill=True, padding=0)

        # Create pane add it to the box.
        paned = Gtk.Paned(expand=True)
        self.box.pack_end(paned, expand=False, fill=True, padding=0)

        # Add a box as the first child of the pane.
        paned_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        paned.add(paned_box)

        # Add a SearchEntry and scrolled window to the left hand side of
        # the vertically separated box.
        self.search_entry = Gtk.SearchEntry()
        paned_box.add(self.search_entry)
        scrolled_window_l = Gtk.ScrolledWindow(expand=True)
        paned_box.add(scrolled_window_l)

        # Add a GtkTreeView to the GtkScrolledWindow.
        self.tree_view = Gtk.TreeView(
            search_column=0,
            level_indentation=1
        )
        scrolled_window_l.add(self.tree_view)

        # Assemble the GtkTreeView columns
        tag_crt = Gtk.CellRendererText()
        tag_tvc = Gtk.TreeViewColumn("tags")
        tag_tvc.pack_start(tag_crt, True)
        tag_tvc.add_attribute(tag_crt, "text", 0)
        self.tree_view.append_column(tag_tvc)

        # Add a scrolled window to the right hand side of the vertically
        # separated paned.
        scrolled_window_r = Gtk.ScrolledWindow(expand=True)
        paned.add(scrolled_window_r)
        self.icon_view = Gtk.IconView()
        scrolled_window_r.add(self.icon_view)

        # Set up stores behind the GUI.
        self.tag_tree_store = Gtk.TreeStore(str)
        self.tree_view.set_model(self.tag_tree_store)
        self.icon_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        self.icon_view.set_model(self.icon_store)
        self.icon_view.set_pixbuf_column(0)
        self.icon_view.set_text_column(1)

        # Bring up default settings.
        self.refresh_treeview()
        self.refresh_iconview()

        node = self.tag_tree_store.append(None, ['asdf', ])
        self.tag_tree_store.append(node, ['wert', ])

        self.show_all()

    def import_files_from_folder(self, unused_calling_widget):
        fcd = Gtk.FileChooserDialog(
            "Import from...", self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             "Select", Gtk.ResponseType.OK))
        fcd.set_default_size(800, 400)

        response = fcd.run()
        if response == Gtk.ResponseType.OK:
            file_path = fcd.get_filename()
            logger.debug("Folder selected: " + file_path)
            self.tag_db.import_files(file_path)
            self.refresh_iconview()
        elif response == Gtk.ResponseType.CANCEL:
            logger.debug("Folder selection cancelled.")
        fcd.destroy()

    def import_file(self, unused_calling_widget):
        fcd = Gtk.FileChooserDialog(
            "Import from...", self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             "Select", Gtk.ResponseType.OK))
        fcd.set_default_size(800, 400)

        response = fcd.run()
        if response == Gtk.ResponseType.OK:
            file_path = fcd.get_filename()
            logger.debug("File selected: " + file_path)
            self.tag_db.import_files(file_path)
            self.refresh_iconview()
        elif response == Gtk.ResponseType.CANCEL:
            logger.debug("File selection cancelled.")
        fcd.destroy()

    def refresh_iconview(self, tag_str=None):

        # Save a lot of processing power by disabling
        self.icon_view.freeze_child_notify()
        self.icon_view.set_model(None)

        self.icon_store.clear()
        if tag_str is None:
            for tracked_file in self.tag_db.session.query(TrackedFile):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    tracked_file.filepath, 100, 100)
                self.icon_store.append((pixbuf, tracked_file.filename))
        else:
            for tracked_file in self.tag_db.session.query(TrackedFile).\
                    select_from(Tag).\
                    filter(Tag.name == tag_str):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    tracked_file.filepath)
                self.icon_store.append((pixbuf, tracked_file.filename))

        # Restore linkage to icon view.
        self.icon_view.set_model(self.icon_store)
        self.icon_view.thaw_child_notify()

    def refresh_treeview(self):
        """Add the tags to the side-bar GtkTreeView."""

        def tag_recurse(tag):
            for child_tag in tag.child_tags:
                self.tag_store.append(tag, [child_tag, ])
                tag_recurse(child_tag)

        self.tag_tree_store.clear()
        for tag in self.tag_db.session.query(Tag):
            if not tag.parent_tags:
                self.tag_store.append(None, [tag])
                tag_recurse(tag)


class MainWindowMenuBar(Gtk.MenuBar):

    def __init__(self, parent, **properties):
        self.parent = parent
        super(MainWindowMenuBar, self).__init__(**properties)

        self.__add_file_menu()
        self.__add_edit_menu()
        self.__add_view_menu()
        self.__add_help_menu()

    def __add_file_menu(self):
        """Create 'File' menu."""
        menuitem = Gtk.MenuItem(label='File')
        self.add(menuitem)
        menu = Gtk.Menu()
        menuitem.set_submenu(menu)

        # Add 'Import from folder' entry.
        about_item = Gtk.ImageMenuItem(label="Import from folder")
        about_item.connect(
            "activate", self.parent.import_files_from_folder)
        menu.add(about_item)

        # Add 'Import from folder' entry.
        about_item = Gtk.ImageMenuItem(label="Import file")
        about_item.connect(
            "activate", self.parent.import_file)
        menu.add(about_item)

    def __add_edit_menu(self):
        """Create 'Edit' menu."""
        menuitem = Gtk.MenuItem(label='Edit')
        self.add(menuitem)
        menu = Gtk.Menu()
        menuitem.set_submenu(menu)

    def __add_view_menu(self):
        """Create 'View' menu."""
        menuitem = Gtk.MenuItem(label='View')
        self.add(menuitem)
        menu = Gtk.Menu()
        menuitem.set_submenu(menu)

    def __add_help_menu(self):
        """Create 'Help' menu."""
        menuitem = Gtk.MenuItem(label='Help')
        self.add(menuitem)
        menu = Gtk.Menu()
        menuitem.set_submenu(menu)

        # Add 'About' entry.
        about_item = Gtk.ImageMenuItem(
            label=Gtk.STOCK_ABOUT, use_stock=True)
        about_item.connect("activate", self.about_clicked)
        menu.add(about_item)

    def about_clicked(self, unused_calling_widget):
        dialog = AboutDialog(self.parent)
        dialog.run()
        dialog.destroy()


class AboutDialog(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(
            self, "About Taginator", parent, 0,
            (Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.set_default_size(400, 30)

        label = Gtk.Label(
            "Taginator is intended as a maintainable, extensible Shotwell "
            "replacement, written in Python and using SQLAlchemy for "
            "flexibility with its database back-end.",
            wrap=True)

        box = self.get_content_area()
        box.add(label)
        self.show_all()
