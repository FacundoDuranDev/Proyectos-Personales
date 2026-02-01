from typing import Dict, List

from ..core.engine import StreamEngine


def build_control_panel(engine: StreamEngine) -> Dict[str, List[object]]:
    try:
        import ipywidgets as widgets
        from IPython.display import display
    except ImportError as exc:
        raise ImportError(
            "Instala ipywidgets para usar el panel: python -m pip install ipywidgets"
        ) from exc

    cfg = engine.get_config()
    fps = widgets.IntSlider(value=cfg.fps, min=5, max=60, description="FPS")
    grid_w = widgets.IntSlider(
        value=cfg.grid_w, min=40, max=200, description="Grid W"
    )
    grid_h = widgets.IntSlider(
        value=cfg.grid_h, min=20, max=120, description="Grid H"
    )
    contrast = widgets.FloatSlider(
        value=cfg.contrast, min=0.5, max=3.0, step=0.1, description="Contraste"
    )
    brightness = widgets.IntSlider(
        value=cfg.brightness, min=-50, max=50, step=1, description="Brillo"
    )
    invert = widgets.Checkbox(value=cfg.invert, description="Invertir")

    def on_change(_):
        engine.update_config(
            fps=fps.value,
            grid_w=grid_w.value,
            grid_h=grid_h.value,
            contrast=contrast.value,
            brightness=brightness.value,
            invert=invert.value,
        )

    for w in [fps, grid_w, grid_h, contrast, brightness, invert]:
        w.observe(on_change, names="value")

    filter_boxes = []
    for filter_obj in engine.filters:
        name = getattr(filter_obj, "name", filter_obj.__class__.__name__)
        enabled = getattr(filter_obj, "enabled", True)
        checkbox = widgets.Checkbox(value=enabled, description=name)

        def _toggle(change, target=filter_obj):
            if hasattr(target, "enabled"):
                setattr(target, "enabled", change["new"])

        checkbox.observe(_toggle, names="value")
        filter_boxes.append(checkbox)

    display(widgets.VBox([fps, grid_w, grid_h, contrast, brightness, invert]))
    if filter_boxes:
        display(widgets.VBox(filter_boxes))

    return {"config": [fps, grid_w, grid_h, contrast, brightness, invert], "filters": filter_boxes}
