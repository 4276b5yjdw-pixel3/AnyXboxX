//! The launcher's look: a dusk gradient (night purple to magenta to a warm orange glow), dark
//! translucent cards with a pink edge, pill tabs and a pink-to-orange progress bar. Colours only:
//! no logo, wordmark or font of any game. The colour maths is plain and tested; the painting
//! helpers only call it.

use eframe::egui::{
    self, Color32, CornerRadius, Margin, Rect, RichText, Shadow, Stroke, Ui, epaint::Mesh, pos2,
    vec2,
};

pub const NIGHT: Color32 = Color32::from_rgb(0x1a, 0x0b, 0x2e);
pub const VIOLET: Color32 = Color32::from_rgb(0x4b, 0x1d, 0x6e);
pub const MAGENTA: Color32 = Color32::from_rgb(0xc2, 0x18, 0x5b);
pub const GLOW: Color32 = Color32::from_rgb(0xff, 0x8a, 0x3d);
pub const HOT_PINK: Color32 = Color32::from_rgb(0xff, 0x2d, 0x95);
pub const TEXT: Color32 = Color32::from_rgb(0xf7, 0xf0, 0xff);
pub const TEXT_MUTED: Color32 = Color32::from_rgb(0xcf, 0xc0, 0xe6);
pub const GOOD: Color32 = Color32::from_rgb(0x5d, 0xe0, 0x8a);
pub const BAD: Color32 = Color32::from_rgb(0xff, 0x7a, 0x8a);
pub const WARN: Color32 = Color32::from_rgb(0xff, 0xc8, 0x6b);

/// The card colour (dark, translucent) and its opacity over the gradient.
pub const CARD_RGB: [u8; 3] = [0x14, 0x08, 0x24];
pub const CARD_ALPHA: u8 = 215;

/// Gradient stops from the top of the window to the bottom.
const STOPS: [(f32, Color32); 4] = [(0.0, NIGHT), (0.42, VIOLET), (0.80, MAGENTA), (1.0, GLOW)];

#[cfg(test)]
fn lerp_channel(a: u8, b: u8, t: f32) -> u8 {
    (f32::from(a) + (f32::from(b) - f32::from(a)) * t).round() as u8
}

/// The gradient colour at `t` (0 = top, 1 = bottom); `t` is clamped.
#[cfg(test)]
pub fn gradient_at(t: f32) -> Color32 {
    let t = t.clamp(0.0, 1.0);
    for pair in STOPS.windows(2) {
        let (t0, c0) = pair[0];
        let (t1, c1) = pair[1];
        if t <= t1 {
            let local = (t - t0) / (t1 - t0);
            return Color32::from_rgb(
                lerp_channel(c0.r(), c1.r(), local),
                lerp_channel(c0.g(), c1.g(), local),
                lerp_channel(c0.b(), c1.b(), local),
            );
        }
    }
    GLOW
}

#[cfg(test)]
fn linear(channel: u8) -> f64 {
    let c = f64::from(channel) / 255.0;
    if c <= 0.039_28 {
        c / 12.92
    } else {
        ((c + 0.055) / 1.055).powf(2.4)
    }
}

#[cfg(test)]
fn luminance(color: Color32) -> f64 {
    0.2126 * linear(color.r()) + 0.7152 * linear(color.g()) + 0.0722 * linear(color.b())
}

/// WCAG contrast ratio between two opaque colours.
#[cfg(test)]
pub fn contrast_ratio(a: Color32, b: Color32) -> f64 {
    let (la, lb) = (luminance(a), luminance(b));
    let (hi, lo) = if la >= lb { (la, lb) } else { (lb, la) };
    (hi + 0.05) / (lo + 0.05)
}

/// What a card looks like when it sits over `behind`.
#[cfg(test)]
pub fn card_over(behind: Color32) -> Color32 {
    let a = f32::from(CARD_ALPHA) / 255.0;
    Color32::from_rgb(
        lerp_channel(behind.r(), CARD_RGB[0], a),
        lerp_channel(behind.g(), CARD_RGB[1], a),
        lerp_channel(behind.b(), CARD_RGB[2], a),
    )
}

fn card_fill() -> Color32 {
    Color32::from_rgba_unmultiplied(CARD_RGB[0], CARD_RGB[1], CARD_RGB[2], CARD_ALPHA)
}

/// Installs the dark visuals and the spacing of the launcher.
pub fn apply(ctx: &egui::Context) {
    let mut visuals = egui::Visuals::dark();
    visuals.override_text_color = Some(TEXT);
    visuals.panel_fill = Color32::TRANSPARENT;
    visuals.window_fill = Color32::from_rgb(0x22, 0x0e, 0x3c);
    visuals.window_stroke = Stroke::new(1.0_f32, HOT_PINK.gamma_multiply(0.6));
    visuals.window_corner_radius = CornerRadius::same(16);
    visuals.extreme_bg_color = Color32::from_rgb(0x10, 0x06, 0x1c);
    visuals.hyperlink_color = Color32::from_rgb(0xff, 0xb3, 0xdd);
    visuals.selection.bg_fill = HOT_PINK.gamma_multiply(0.55);
    visuals.selection.stroke = Stroke::new(1.0_f32, TEXT);
    let widgets = &mut visuals.widgets;
    widgets.inactive.bg_fill = Color32::from_rgb(0x3a, 0x17, 0x5c);
    widgets.inactive.weak_bg_fill = Color32::from_rgb(0x3a, 0x17, 0x5c);
    widgets.inactive.corner_radius = CornerRadius::same(10);
    widgets.hovered.bg_fill = Color32::from_rgb(0x8a, 0x1f, 0x7a);
    widgets.hovered.weak_bg_fill = Color32::from_rgb(0x8a, 0x1f, 0x7a);
    widgets.hovered.corner_radius = CornerRadius::same(10);
    widgets.hovered.bg_stroke = Stroke::new(1.0_f32, HOT_PINK);
    widgets.active.bg_fill = HOT_PINK;
    widgets.active.weak_bg_fill = HOT_PINK;
    widgets.active.corner_radius = CornerRadius::same(10);
    widgets.open.corner_radius = CornerRadius::same(10);
    ctx.set_visuals(visuals);
    ctx.global_style_mut(|style| {
        style.spacing.item_spacing = vec2(10.0, 8.0);
        style.spacing.button_padding = vec2(14.0, 7.0);
        for (text_style, size) in [
            (egui::TextStyle::Heading, 28.0),
            (egui::TextStyle::Body, 15.0),
            (egui::TextStyle::Button, 15.0),
            (egui::TextStyle::Monospace, 13.0),
        ] {
            if let Some(font) = style.text_styles.get_mut(&text_style) {
                font.size = size;
            }
        }
    });
}

/// The vertical gradient as one mesh with a pair of vertices per stop.
pub fn gradient_mesh(rect: Rect) -> Mesh {
    let mut mesh = Mesh::default();
    let mut previous = None;
    for (t, color) in STOPS {
        let y = rect.top() + rect.height() * t;
        let left = mesh.vertices.len() as u32;
        mesh.colored_vertex(pos2(rect.left(), y), color);
        mesh.colored_vertex(pos2(rect.right(), y), color);
        if let Some(prev) = previous {
            mesh.add_triangle(prev, prev + 1, left);
            mesh.add_triangle(prev + 1, left + 1, left);
        }
        previous = Some(left);
    }
    mesh
}

/// Paints the gradient behind everything.
pub fn paint_background(ctx: &egui::Context) {
    let rect = ctx.content_rect();
    ctx.layer_painter(egui::LayerId::background())
        .add(egui::Shape::mesh(gradient_mesh(rect)));
}

/// A translucent dark card with a pink edge glow.
pub fn card<R>(ui: &mut Ui, add: impl FnOnce(&mut Ui) -> R) -> R {
    egui::Frame::new()
        .fill(card_fill())
        .stroke(Stroke::new(1.0_f32, HOT_PINK.gamma_multiply(0.45)))
        .corner_radius(CornerRadius::same(16))
        .inner_margin(Margin::same(16))
        .shadow(Shadow {
            offset: [0, 0],
            blur: 22,
            spread: 1,
            color: HOT_PINK.gamma_multiply(0.22),
        })
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            add(ui)
        })
        .inner
}

/// The page tab as a pill; returns true when clicked.
pub fn tab_pill(ui: &mut Ui, selected: bool, label: &str) -> bool {
    let (fill, text) = if selected {
        (BUTTON_PINK, Color32::WHITE)
    } else {
        (Color32::from_rgba_unmultiplied(20, 8, 36, 170), TEXT)
    };
    let button = egui::Button::new(RichText::new(label).strong().color(text))
        .fill(fill)
        .stroke(Stroke::new(1.0_f32, HOT_PINK.gamma_multiply(0.6)))
        .corner_radius(CornerRadius::same(255))
        .min_size(vec2(0.0, 34.0));
    ui.add(button).clicked()
}

/// Spacing scale: every gap in the window is one of these.
pub const SP_XS: f32 = 4.0;
pub const SP_S: f32 = 8.0;
pub const SP_M: f32 = 16.0;
pub const SP_L: f32 = 24.0;

/// The fill of buttons that carry white text (5:1 or better), and its hovered form.
pub const BUTTON_PINK: Color32 = Color32::from_rgb(0xd4, 0x14, 0x7a);
pub const BUTTON_PINK_HOVER: Color32 = Color32::from_rgb(0xd9, 0x18, 0x7e);
const BUTTON_OFF: Color32 = Color32::from_rgb(0x4a, 0x2a, 0x66);

/// The main button: a pink pill that grows and glows under the pointer, and pulses while
/// `pulsing` (a launch is under way). Returns the response; a disabled one never reports a click.
pub fn glow_button(
    ui: &mut Ui,
    enabled: bool,
    label: &str,
    min_size: egui::Vec2,
    pulsing: bool,
) -> egui::Response {
    let font = egui::FontId::proportional(if min_size.y > 48.0 { 24.0 } else { 15.0 });
    let text = ui
        .painter()
        .layout_no_wrap(label.to_string(), font, Color32::WHITE);
    let size = vec2(
        min_size.x.max(text.size().x + 40.0),
        min_size.y.max(text.size().y + 16.0),
    );
    let sense = if enabled {
        egui::Sense::click()
    } else {
        egui::Sense::hover()
    };
    let (rect, response) = ui.allocate_exact_size(size, sense);
    let hover = ui
        .ctx()
        .animate_bool_with_time(response.id, enabled && response.hovered(), 0.15);
    let time = ui.input(|i| i.time);
    let pulse = if pulsing && enabled {
        ui.ctx().request_repaint();
        crate::anim::pulse(time, 1.4)
    } else {
        0.0
    };
    let body = Rect::from_center_size(rect.center(), size * (1.0 + 0.04 * hover));
    let radius = CornerRadius::same((body.height() / 2.0).min(255.0) as u8);
    let painter = ui.painter();
    if enabled {
        let strength = 0.22 + 0.5 * hover + 0.5 * pulse;
        for layer in 1..=5_u8 {
            let alpha = (strength * 70.0 / f32::from(layer)).min(255.0) as u8;
            painter.rect_filled(
                body.expand(f32::from(layer) * 3.5),
                CornerRadius::same(((body.height() / 2.0) as u8).saturating_add(layer * 3)),
                Color32::from_rgba_unmultiplied(0xff, 0x2d, 0x95, alpha),
            );
        }
    }
    let fill = if enabled {
        lerp_color(BUTTON_PINK, BUTTON_PINK_HOVER, hover)
    } else {
        BUTTON_OFF
    };
    painter.rect_filled(body, radius, fill);
    painter.rect_stroke(
        body,
        radius,
        Stroke::new(1.0_f32, Color32::WHITE.gamma_multiply(0.25 + 0.4 * hover)),
        egui::StrokeKind::Inside,
    );
    painter.galley(body.center() - text.size() / 2.0, text, Color32::WHITE);
    if enabled {
        response.on_hover_cursor(egui::CursorIcon::PointingHand)
    } else {
        response
    }
}

fn lerp_color(a: Color32, b: Color32, t: f32) -> Color32 {
    let mix = |x: u8, y: u8| {
        (f32::from(x) + (f32::from(y) - f32::from(x)) * t.clamp(0.0, 1.0)).round() as u8
    };
    Color32::from_rgb(mix(a.r(), b.r()), mix(a.g(), b.g()), mix(a.b(), b.b()))
}

/// A status chip: a coloured dot and a short text on a dark pill.
pub fn chip(ui: &mut Ui, color: Color32, text: &str) {
    let font = egui::FontId::proportional(14.0);
    let galley = ui.painter().layout_no_wrap(text.to_string(), font, TEXT);
    let size = vec2(galley.size().x + 38.0, 30.0);
    let (rect, _) = ui.allocate_exact_size(size, egui::Sense::hover());
    let painter = ui.painter();
    painter.rect_filled(
        rect,
        CornerRadius::same(15),
        Color32::from_rgba_unmultiplied(0x10, 0x06, 0x1c, 235),
    );
    painter.rect_stroke(
        rect,
        CornerRadius::same(15),
        Stroke::new(1.0_f32, color.gamma_multiply(0.7)),
        egui::StrokeKind::Inside,
    );
    painter.circle_filled(pos2(rect.left() + 15.0, rect.center().y), 5.0, color);
    painter.galley(
        pos2(rect.left() + 28.0, rect.center().y - galley.size().y / 2.0),
        galley,
        TEXT,
    );
}

/// An on/off switch that slides; returns true when it was flipped this frame.
pub fn toggle(ui: &mut Ui, value: &mut bool) -> bool {
    let size = vec2(46.0, 26.0);
    let (rect, mut response) = ui.allocate_exact_size(size, egui::Sense::click());
    let flipped = response.clicked();
    if flipped {
        *value = !*value;
        response.mark_changed();
    }
    let on = ui.ctx().animate_bool_with_time(response.id, *value, 0.14);
    let track = lerp_color(Color32::from_rgb(0x3a, 0x17, 0x5c), BUTTON_PINK, on);
    let painter = ui.painter();
    painter.rect_filled(rect, CornerRadius::same(13), track);
    painter.rect_stroke(
        rect,
        CornerRadius::same(13),
        Stroke::new(1.0_f32, HOT_PINK.gamma_multiply(0.6)),
        egui::StrokeKind::Inside,
    );
    let x = rect.left() + 13.0 + (rect.width() - 26.0) * on;
    painter.circle_filled(pos2(x, rect.center().y), 9.5, Color32::WHITE);
    response.on_hover_cursor(egui::CursorIcon::PointingHand);
    flipped
}

/// A progress bar filled with a pink-to-orange gradient, with its text on top. A light band
/// sweeps across the filled part; with no fraction (length unknown) a band slides along the track.
pub fn gradient_bar(ui: &mut Ui, fraction: Option<f32>, text: &str) {
    let height = 26.0;
    let (rect, _) =
        ui.allocate_exact_size(vec2(ui.available_width(), height), egui::Sense::hover());
    let radius = CornerRadius::same(13);
    let time = ui.input(|i| i.time);
    ui.ctx()
        .request_repaint_after(std::time::Duration::from_millis(33));
    let painter = ui.painter().clone();
    painter.rect_filled(rect, radius, Color32::from_rgb(0x10, 0x06, 0x1c));
    let fill = match fraction {
        Some(f) if f > 0.0 => {
            let width = (rect.width() * f.clamp(0.0, 1.0))
                .max(height)
                .min(rect.width());
            Some(Rect::from_min_size(rect.min, vec2(width, height)))
        }
        Some(_) => None,
        None => {
            let (a, b) = crate::anim::moving_band(time, 1.6);
            let x0 = rect.left() + rect.width() * a;
            let x1 = rect.left() + rect.width() * b;
            (x1 - x0 > 1.0)
                .then(|| Rect::from_min_max(pos2(x0, rect.top()), pos2(x1, rect.bottom())))
        }
    };
    if let Some(fill) = fill {
        painter.add(egui::Shape::mesh(horizontal_mesh(fill, HOT_PINK, GLOW)));
        if fraction.is_some() {
            let (a, b) = crate::anim::moving_band(time, 1.8);
            let band = Rect::from_min_max(
                pos2(fill.left() + fill.width() * a, fill.top()),
                pos2(fill.left() + fill.width() * b, fill.bottom()),
            );
            let clear = Color32::from_rgba_unmultiplied(255, 255, 255, 0);
            let bright = Color32::from_rgba_unmultiplied(255, 255, 255, 70);
            if band.width() > 1.0 {
                let mid = band.center().x;
                painter.add(egui::Shape::mesh(horizontal_mesh(
                    Rect::from_min_max(band.min, pos2(mid, band.bottom())),
                    clear,
                    bright,
                )));
                painter.add(egui::Shape::mesh(horizontal_mesh(
                    Rect::from_min_max(pos2(mid, band.top()), band.max),
                    bright,
                    clear,
                )));
            }
        }
    }
    painter.rect_stroke(
        rect,
        radius,
        Stroke::new(1.0_f32, HOT_PINK.gamma_multiply(0.5)),
        egui::StrokeKind::Inside,
    );
    painter.text(
        rect.center(),
        egui::Align2::CENTER_CENTER,
        text,
        egui::FontId::proportional(14.0),
        Color32::WHITE,
    );
}

/// A quad shaded from `left` to `right`.
fn horizontal_mesh(rect: Rect, left: Color32, right: Color32) -> Mesh {
    let mut mesh = Mesh::default();
    mesh.colored_vertex(rect.left_top(), left);
    mesh.colored_vertex(rect.left_bottom(), left);
    mesh.colored_vertex(rect.right_top(), right);
    mesh.colored_vertex(rect.right_bottom(), right);
    mesh.add_triangle(0, 1, 2);
    mesh.add_triangle(1, 3, 2);
    mesh
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gradient_hits_its_stops_and_clamps() {
        assert_eq!(gradient_at(0.0), NIGHT);
        assert_eq!(gradient_at(0.42), VIOLET);
        assert_eq!(gradient_at(1.0), GLOW);
        assert_eq!(gradient_at(-3.0), NIGHT);
        assert_eq!(gradient_at(9.0), GLOW);
    }

    #[test]
    fn gradient_goes_from_dark_to_bright() {
        assert!(luminance(gradient_at(0.0)) < luminance(gradient_at(0.5)));
        assert!(luminance(gradient_at(0.5)) < luminance(gradient_at(1.0)));
    }

    #[test]
    fn text_on_cards_meets_wcag_aa_over_the_whole_gradient() {
        for i in 0..=20 {
            let card = card_over(gradient_at(i as f32 / 20.0));
            assert!(contrast_ratio(TEXT, card) >= 4.5, "body text at {i}");
            assert!(contrast_ratio(TEXT_MUTED, card) >= 4.5, "muted text at {i}");
            for status in [GOOD, BAD, WARN] {
                assert!(contrast_ratio(status, card) >= 4.5, "status colour at {i}");
            }
        }
    }

    #[test]
    fn white_text_on_the_button_pinks_meets_wcag_aa() {
        assert!(contrast_ratio(Color32::WHITE, BUTTON_PINK) >= 4.5);
        assert!(contrast_ratio(Color32::WHITE, BUTTON_PINK_HOVER) >= 4.5);
    }

    #[test]
    fn lerp_color_runs_between_its_ends() {
        assert_eq!(lerp_color(NIGHT, GLOW, 0.0), NIGHT);
        assert_eq!(lerp_color(NIGHT, GLOW, 1.0), GLOW);
        assert_eq!(lerp_color(NIGHT, GLOW, 9.0), GLOW);
    }

    #[test]
    fn contrast_of_black_on_white_is_21() {
        let ratio = contrast_ratio(Color32::BLACK, Color32::WHITE);
        assert!((ratio - 21.0).abs() < 0.01);
    }

    #[test]
    fn gradient_mesh_covers_the_rect() {
        let rect = Rect::from_min_max(pos2(0.0, 0.0), pos2(100.0, 200.0));
        let mesh = gradient_mesh(rect);
        assert_eq!(mesh.vertices.len(), STOPS.len() * 2);
        assert_eq!(mesh.indices.len(), (STOPS.len() - 1) * 6);
        assert_eq!(mesh.calc_bounds(), rect);
    }
}
