from typing import Optional

from gi.repository import Gtk

from opendrop.app.common.footer.linearnav import linear_navigator_footer_cs
from opendrop.app.common.wizard import WizardPageControls
from opendrop.mvp import ComponentSymbol, Presenter, View
from opendrop.utility.bindable import Bindable
from opendrop.utility.bindablegext import GObjectPropertyBindable
from .configurator import configurator_cs
from .model import ImageAcquisitionModel, AcquirerType

image_acquisition_cs = ComponentSymbol()  # type: ComponentSymbol[Gtk.Widget]


@image_acquisition_cs.view(options=['footer_area'])
class ImageAcquisitionView(View['ImageAcquisitionPresenter', Gtk.Widget]):
    def _do_init(self, footer_area: Gtk.Grid) -> Gtk.Widget:
        self._widget = Gtk.Grid(margin=10, column_spacing=10, row_spacing=10)

        image_source_lbl = Gtk.Label('Image source:')
        self._widget.attach(image_source_lbl, 0, 0, 1, 1)

        self._image_source_combobox = Gtk.ComboBoxText(hexpand=True, halign=Gtk.Align.START)
        self._widget.attach(self._image_source_combobox, 1, 0, 1, 1)

        self._populate_combobox()

        self._widget.attach(
            Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True),
            0, 1, 2, 1
        )

        _, configurator_area = self.new_component(
            configurator_cs.factory(
                in_acquirer=self.presenter.bn_acquirer
            )
        )
        self._widget.attach(configurator_area, 0, 2, 2, 1)

        self.bn_selected_acquirer_type = GObjectPropertyBindable(
            g_obj=self._image_source_combobox,
            prop_name='active-id',
            transform_to=lambda e: e.name if e is not None else None,
            transform_from=lambda name: AcquirerType[name] if name is not None else None,
        )  # type: Bindable[Optional[str]]

        _, footer_inside = self.new_component(
            linear_navigator_footer_cs.factory(
                do_next=self.presenter.next_page
            )
        )
        footer_inside.show()
        footer_area.add(footer_inside)

        self.presenter.view_ready()

        self._widget.foreach(Gtk.Widget.show)

        return self._widget

    def _populate_combobox(self) -> None:
        for acquirer_type in AcquirerType:
            self._image_source_combobox.append(
                id=acquirer_type.name,
                text=acquirer_type.display_name,
            )

    def _do_destroy(self) -> None:
        self._widget.destroy()


@image_acquisition_cs.presenter(options=['model', 'page_controls'])
class ImageAcquisitionPresenter(Presenter['ImageAcquisitionView']):
    def _do_init(self, model: ImageAcquisitionModel, page_controls: WizardPageControls) -> None:
        self._model = model
        self._page_controls = page_controls

        self.bn_acquirer = model.bn_acquirer

        self.__event_connections = []

    def view_ready(self) -> None:
        self.__event_connections.extend([
            self._model.bn_acquirer.on_changed.connect(self._hdl_model_acquirer_changed),
            self.view.bn_selected_acquirer_type.on_changed.connect(self._hdl_selected_acquirer_type_changed),
        ])

        self._hdl_model_acquirer_changed()

    def _hdl_model_acquirer_changed(self) -> None:
        acquirer_type = self._model.get_acquirer_type()
        self.view.bn_selected_acquirer_type.set(acquirer_type)

    def _hdl_selected_acquirer_type_changed(self) -> None:
        selected_acquirer_type = self.view.bn_selected_acquirer_type.get()
        self._model.use_acquirer_type(selected_acquirer_type)

    def next_page(self) -> None:
        self._page_controls.next_page()

    def _do_destroy(self) -> None:
        for ec in self.__event_connections:
            ec.disconnect()
