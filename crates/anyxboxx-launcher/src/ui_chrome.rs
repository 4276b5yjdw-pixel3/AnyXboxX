//! The window's frame: the left navigation, the console drawer at the bottom and the toasts.

use eframe::egui::{self, Align2, Color32, CornerRadius, RichText, Stroke, Ui, pos2, vec2};

use crate::app::{App, Tab};
use crate::loglevel::{self, Level};
use crate::toast::Kind;
use crate::{anim, theme};

/// Width of the left navigation.
pub const SIDEBAR_WIDTH: f32 = 212.0;
const CONSOLE_HEIGHT: f32 = 230.0;

/// The pages in the navigation, with their icon and name.
const PAGES: [(Tab, &str, &str); 5] = [
    (Tab::Home, "\u{1F3E0}", "Home"),
    (Tab::Setup, "\u{1F527}", "Setup"),
    (Tab::Files, "\u{1F4C1}", "Game folder"),
    (Tab::Shaders, "\u{2728}", "Shaders"),
    (Tab::Play, "\u{1F3AE}", "Play"),
];

/// The navigation: the name on top, then one row per page.
pub fn sidebar(app: &mut App, ui: &mut Ui) {
    ui.add_space(theme::SP_S);
    ui.label(RichText::new("AnyXboxX").size(28.0).strong());
    ui.label(RichText::new("Xbox games on Windows").color(theme::TEXT_MUTED));
    ui.add_space(theme::SP_L);
    for (tab, icon, label) in PAGES {
        if nav_row(ui, app.tab == tab, icon, label) {
            app.tab = tab;
        }
    }
}

fn nav_row(ui: &mut Ui, selected: bool, icon: &str, label: &str) -> bool {
    let (rect, response) =
        ui.allocate_exact_size(vec2(ui.available_width(), 46.0), egui::Sense::click());
    let hover = ui
        .ctx()
        .animate_bool_with_time(response.id, response.hovered(), 0.12);
    let radius = CornerRadius::same(14);
    let painter = ui.painter();
    if selected {
        painter.rect_filled(rect, radius, theme::BUTTON_PINK);
    } else if hover > 0.0 {
        painter.rect_filled(
            rect,
            radius,
            Color32::from_rgba_unmultiplied(0xff, 0x2d, 0x95, (60.0 * hover) as u8),
        );
    }
    let color = if selected {
        Color32::WHITE
    } else {
        theme::TEXT
    };
    painter.text(
        pos2(rect.left() + 26.0, rect.center().y),
        Align2::CENTER_CENTER,
        icon,
        egui::FontId::proportional(19.0),
        color,
    );
    painter.text(
        pos2(rect.left() + 50.0, rect.center().y),
        Align2::LEFT_CENTER,
        label,
        egui::FontId::proportional(16.0),
        color,
    );
    response
        .on_hover_cursor(egui::CursorIcon::PointingHand)
        .clicked()
}

fn level_color(level: Level) -> Color32 {
    match level {
        Level::Step => theme::TEXT,
        Level::Error => theme::BAD,
        Level::Warn => theme::WARN,
        Level::Info => theme::TEXT_MUTED,
    }
}

/// The drawer's header row, always on screen: a button that opens the log, and "Clear".
pub fn console_header(app: &mut App, ui: &mut Ui) {
    ui.horizontal(|ui| {
        let arrow = if app.drawer_open { "v" } else { ">" };
        let label = format!("Console {arrow}  {} lines", app.log.len());
        if theme::tab_pill(ui, app.drawer_open, &label) {
            app.drawer_open = !app.drawer_open;
        }
        if app.drawer_open && ui.small_button("Clear").clicked() {
            app.log.clear();
        }
    });
}

/// The log, one colour per level, newest at the bottom.
pub fn console_body(app: &App, ui: &mut Ui) {
    theme::card(ui, |ui| {
        egui::ScrollArea::vertical()
            .id_salt("log")
            .stick_to_bottom(true)
            .auto_shrink([false, false])
            .max_height(CONSOLE_HEIGHT - 60.0)
            .show(ui, |ui| {
                if app.log.is_empty() {
                    ui.label(
                        RichText::new(
                            "Nothing yet: the output of the build and of the game lands here.",
                        )
                        .color(theme::TEXT_MUTED),
                    );
                }
                for line in &app.log {
                    let level = loglevel::classify_line(line);
                    let mut text = RichText::new(line).monospace().color(level_color(level));
                    if level == Level::Step {
                        text = text.strong();
                    }
                    ui.label(text);
                }
            });
    });
}

/// Height of the console drawer's body.
pub const fn console_height() -> f32 {
    CONSOLE_HEIGHT
}

fn kind_color(kind: Kind) -> Color32 {
    match kind {
        Kind::Success => theme::GOOD,
        Kind::Error => theme::BAD,
        Kind::Info => theme::HOT_PINK,
    }
}

/// The toasts, stacked at the top right, fading in and out.
pub fn toasts(app: &mut App, ctx: &egui::Context) {
    let now = ctx.input(|i| i.time);
    app.toasts.prune(now);
    if app.toasts.is_empty() {
        return;
    }
    egui::Area::new(egui::Id::new("toasts"))
        .anchor(Align2::RIGHT_TOP, vec2(-theme::SP_M, theme::SP_M))
        .order(egui::Order::Tooltip)
        .show(ctx, |ui| {
            for toast in app.toasts.visible() {
                let alpha = toast.alpha(now);
                let slide = (1.0 - anim::ease_out_cubic(((now - toast.born) / 0.25) as f32)) * 24.0;
                ui.add_space(0.0);
                ui.scope(|ui| {
                    ui.set_opacity(alpha);
                    ui.set_max_width(360.0);
                    egui::Frame::new()
                        .fill(Color32::from_rgb(0x1a, 0x0b, 0x2e))
                        .stroke(Stroke::new(1.5_f32, kind_color(toast.kind)))
                        .corner_radius(CornerRadius::same(14))
                        .inner_margin(egui::Margin::symmetric(14, 10))
                        .outer_margin(egui::Margin {
                            left: slide as i8,
                            ..egui::Margin::ZERO
                        })
                        .show(ui, |ui| {
                            ui.label(RichText::new(&toast.text).color(theme::TEXT));
                        });
                });
                ui.add_space(theme::SP_S);
            }
        });
    ctx.request_repaint_after(std::time::Duration::from_millis(33));
}
