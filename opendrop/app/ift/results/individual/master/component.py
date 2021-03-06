from typing import Optional, Sequence, MutableSequence, Callable, Any

from gi.repository import Gtk, Pango

from opendrop.app.ift.analysis import IFTDropAnalysis
from opendrop.mvp import ComponentSymbol, View, Presenter
from opendrop.utility.bindable import Bindable

master_cs = ComponentSymbol()  # type: ComponentSymbol[Gtk.Widget]


@master_cs.view()
class MasterView(View['MasterPresenter', Gtk.Widget]):
    def _do_init(self) -> Gtk.Widget:
        self._widget = Gtk.ScrolledWindow(hexpand=True)

        self._tree_model = Gtk.ListStore(str, str, str)
        self._rows = []  # type: MutableSequence[self.RowManager]

        tree_view = Gtk.TreeView(
            model=self._tree_model,
            enable_search=False,
            enable_grid_lines=Gtk.TreeViewGridLines.BOTH,
        )
        tree_view.show()
        self._widget.add(tree_view)

        self._tree_view = tree_view

        timestamp_col = Gtk.TreeViewColumn(
            title='Timestamp (s)',
            cell_renderer=Gtk.CellRendererText(),
            text=0
        )
        tree_view.append_column(timestamp_col)

        status_col = Gtk.TreeViewColumn(
            title='Status',
            cell_renderer=Gtk.CellRendererText(),
            text=1
        )
        tree_view.append_column(status_col)

        log_col = Gtk.TreeViewColumn(
            title='Log',
            cell_renderer=Gtk.CellRendererText(
                font='Monospace',
                ellipsize=Pango.EllipsizeMode.END
            ),
            text=2
        )
        tree_view.append_column(log_col)

        self._tree_selection = tree_view.get_selection()
        self._tree_selection_changed_id = self._tree_selection.connect(
            'changed',
            self._hdl_tree_selection_changed
        )

        self.presenter.view_ready()

        return self._widget

    def _get_user_selection(self) -> Any:
        _, tree_iter = self._tree_selection.get_selected()
        if tree_iter is None:
            return None

        selected_row_mgr = self._get_row_mgr_from_tree_iter(tree_iter)
        return selected_row_mgr.id

    def set_user_selection(self, row_id: Any) -> None:
        current_selection = self._get_user_selection()
        if row_id is current_selection:
            return

        self._tree_selection.handler_block(self._tree_selection_changed_id)
        try:
            if row_id is None:
                self._tree_selection.unselect_all()
                return
            row_mgr = self._get_row_mgr_from_id(row_id)
            self._tree_selection.select_path(row_mgr.tree_row_ref.get_path())
        finally:
            self._tree_selection.handler_unblock(self._tree_selection_changed_id)

    def _hdl_tree_selection_changed(self, tree_selection: Gtk.TreeSelection) -> None:
        self.presenter.select(self._get_user_selection())

    def new_row(self, row_id: Any) -> None:
        tree_iter = self._tree_model.append((None, None, None))
        row_ref = Gtk.TreeRowReference(
            model=self._tree_model,
            path=self._tree_model.get_path(tree_iter)
        )

        row_mgr = self.RowManager(
            row_id=row_id,
            tree_row_ref=row_ref,
            do_remove=self.remove_row
        )
        self._rows.append(row_mgr)

        if self._get_user_selection() is None and len(self._rows) == 1:
            self.presenter.select(row_id)

        self._widget.queue_resize()
        self._tree_view.queue_resize()
        self._tree_view.queue_allocate()
        self._tree_view.queue_allocate()

    def set_row_timestamp(self, row_id: Any, timestamp: float) -> None:
        row_mgr = self._get_row_mgr_from_id(row_id)
        row_mgr.set_timestamp_text(timestamp)

    def set_row_status_text(self, row_id: Any, text: str) -> None:
        row_mgr = self._get_row_mgr_from_id(row_id)
        row_mgr.set_status_text(text)

    def set_row_log_text(self, row_id: Any, text: str) -> None:
        row_mgr = self._get_row_mgr_from_id(row_id)
        row_mgr.set_log_text(text)

    def remove_row(self, row_id: Any) -> None:
        row_mgr = self._get_row_mgr_from_id(row_id)

        next_row_mgr = None
        if len(self._rows) > 1:
            row_mgr_idx = self._rows.index(row_mgr)
            if row_mgr_idx + 1 < len(self._rows):
                next_row_mgr = self._rows[row_mgr_idx + 1]
            else:
                next_row_mgr = self._rows[row_mgr_idx - 1]

        self._tree_model.remove(row_mgr.tree_iter)
        self._rows.remove(row_mgr)

        if next_row_mgr is not None:
            self.presenter.select(next_row_mgr.id)

    def _get_row_mgr_from_id(self, row_id: Any) -> 'RowManager':
        for row_mgr in self._rows:
            if row_mgr.id == row_id:
                return row_mgr
        else:
            raise ValueError('No row found.')

    def _get_row_mgr_from_tree_iter(self, tree_iter: Gtk.TreeIter) -> 'RowManager':
        tree_path = self._tree_model.get_path(tree_iter)

        for row_mgr in self._rows:
            if row_mgr.tree_row_ref.get_path() == tree_path:
                return row_mgr
        else:
            raise ValueError('No row found.')

    def _do_destroy(self) -> None:
        self._widget.destroy()

    class RowManager:
        TIMESTAMP_COL = 0
        STATUS_COL = 1
        LOG_TEXT_COL = 2

        def __init__(self, row_id: Any, tree_row_ref: Gtk.TreeRowReference,
                     do_remove: Callable[['MasterView.RowManager'], Any]) -> None:
            self.id = row_id
            self.tree_row_ref = tree_row_ref

            self._do_remove = do_remove

        def set_timestamp_text(self, text: float) -> None:
            self._tree_model.set_value(self.tree_iter, column=self.TIMESTAMP_COL, value=text)

        def set_status_text(self, text: str) -> None:
            self._tree_model.set_value(self.tree_iter, column=self.STATUS_COL, value=text)

        def set_log_text(self, text: str) -> None:
            self._tree_model.set_value(self.tree_iter, column=self.LOG_TEXT_COL, value=text)

        @property
        def tree_iter(self) -> Gtk.TreeIter:
            return self._tree_model.get_iter(self.tree_row_ref.get_path())

        @property
        def _tree_model(self) -> Gtk.TreeModel:
            return self.tree_row_ref.get_model()


@master_cs.presenter(options=['bind_selection', 'in_analyses'])
class MasterPresenter(Presenter['MasterView']):
    def _do_init(
            self,
            bind_selection: Bindable[Optional[IFTDropAnalysis]],
            in_analyses: Bindable[Sequence[IFTDropAnalysis]]
    ) -> None:
        self._bn_selection = bind_selection
        self._bn_analyses = in_analyses

        self._row_updaters = {}
        self._tracked_analyses = []

        self.__data_bindings = []
        self.__event_connections = []

    def view_ready(self):
        self.__event_connections.extend([
            self._bn_analyses.on_changed.connect(
                self._hdl_analyses_changed
            ),
            self._bn_selection.on_changed.connect(
                self._hdl_selection_changed
            ),
        ])

        self._hdl_analyses_changed()
        self._hdl_selection_changed()

    def select(self, analysis: IFTDropAnalysis) -> None:
        self._bn_selection.set(analysis)

    def _hdl_analyses_changed(self) -> None:
        source_analyses = self._bn_analyses.get()
        tracked_analyses = self._tracked_analyses

        # Add new analyses in the same order as they appear in `source_analyses`
        to_add = [
            analysis
            for analysis in source_analyses
            if analysis not in tracked_analyses
        ]
        for x in to_add:
            self._add_analysis(x)

        to_remove = set(tracked_analyses) - set(source_analyses)
        for x in to_remove:
            self._remove_analysis(x)

    def _add_analysis(self, analysis: IFTDropAnalysis) -> None:
        self._tracked_analyses.append(analysis)

        self.view.new_row(analysis)

        row_updater = self.RowUpdater(
            analysis=analysis,
            do_set_timestamp_text=(
                lambda timestamp:
                    self.view.set_row_timestamp(row_id=analysis, timestamp=timestamp)
            ),
            do_set_status_text=(
                lambda text:
                    self.view.set_row_status_text(row_id=analysis, text=text)
            ),
            do_set_log_text=(
                lambda text:
                    self.view.set_row_log_text(row_id=analysis, text=text)
            ),
        )

        self._row_updaters[analysis] = row_updater

    def _remove_analysis(self, analysis: IFTDropAnalysis) -> None:
        row_updater = self._row_updaters[analysis]
        row_updater.destroy()

        self.view.remove_row(analysis)

        self._tracked_analyses.remove(analysis)

    def _hdl_selection_changed(self) -> None:
        selected_analysis = self._bn_selection.get()

        if selected_analysis is not None and selected_analysis not in self._tracked_analyses:
            self._add_analysis(selected_analysis)

        self.view.set_user_selection(selected_analysis)

    def _do_destroy(self) -> None:
        for db in self.__data_bindings:
            db.unbind()

        for ec in self.__event_connections:
            ec.disconnect()

        for analysis in tuple(self._tracked_analyses):
            self._remove_analysis(analysis)

    class RowUpdater:
        def __init__(
                self,
                analysis: IFTDropAnalysis,
                do_set_timestamp_text: Callable[[str], Any],
                do_set_status_text: Callable[[str], Any],
                do_set_log_text: Callable[[str], Any]
        ) -> None:
            self._analysis = analysis

            self._do_set_timestamp_text = do_set_timestamp_text
            self._do_set_status_text = do_set_status_text
            self._do_set_log_text = do_set_log_text

            self.__event_connections = [
                analysis.bn_image_timestamp.on_changed.connect(
                    self._update_timestamp
                ),
                analysis.bn_status.on_changed.connect(
                    self._update_status_text
                ),
                analysis.bn_log.on_changed.connect(
                    self._update_log_text
                ),
            ]

            self._update_timestamp()
            self._update_status_text()
            self._update_log_text()

        def _update_timestamp(self) -> None:
            timestamp = self._analysis.bn_image_timestamp.get()
            timestamp_text = format(timestamp, '.1f')
            self._do_set_timestamp_text(timestamp_text)

        def _update_status_text(self) -> None:
            status = self._analysis.bn_status.get()
            status_text = status.display_name
            self._do_set_status_text(status_text)

        def _update_log_text(self) -> None:
            log_history = self._analysis.bn_log.get()
            log_lines = log_history.splitlines()

            if len(log_lines) == 0:
                self._do_set_log_text('')
                return

            log_last_line = log_lines[-1]
            self._do_set_log_text(log_last_line)

        def destroy(self) -> None:
            for ec in self.__event_connections:
                ec.disconnect()
