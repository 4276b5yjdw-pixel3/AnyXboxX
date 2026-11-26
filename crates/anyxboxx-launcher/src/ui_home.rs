//! The landing page: the picture, the big PLAY button and what is ready.

use eframe::egui::{self, Color32, CornerRadius, RichText, Stroke, TextureHandle, Ui, vec2};

use crate::app::{App, Tab};
use crate::home::{self, Readiness};
use crate::host::GpuVendor;
use crate::theme;

/// Width above which the picture sits beside the text.
const WIDE: f32 = 720.0;
const ART_SIDE: f32 = 340.0;

pub fn home(app: &mut App, ui: &mut Ui) {
    let readiness = home::folder_readiness(app.settings.game_path().is_some(), &app.verify);
    let texture = app.splash.texture().cloned();
    theme::card(ui, |ui| {
        if ui.available_width() > WIDE {
            ui.columns(2, |columns| {
                hero_text(app, &mut columns[0], readiness);
                hero_art(texture.as_ref(), &mut columns[1]);
            });
        } else {
            hero_art(texture.as_ref(), ui);
            ui.add_space(theme::SP_M);
            hero_text(app, ui, readiness);
        }
    });
}

fn hero_text(app: &mut App, ui: &mut Ui, readiness: Readiness) {
    ui.label(RichText::new("AnyXboxX").size(46.0).strong());
    ui.label(
        RichText::new("Run your own Xbox game build on this PC. Nothing leaves your machine.")
            .size(16.0)
            .color(theme::TEXT_MUTED),
    );
    ui.add_space(theme::SP_M);
    ui.horizontal_wrapped(|ui| {
        status_chips(app, ui, readiness);
    });
    ui.add_space(theme::SP_L);
    let busy = app.is_busy();
    let verifying = matches!(app.verify, crate::app::Verify::Running);
    let label = home::play_label(readiness, busy, verifying);
    if theme::glow_button(ui, !busy, label, vec2(300.0, 68.0), busy).clicked() {
        press_play(app, readiness);
    }
    ui.add_space(theme::SP_M);
    let options = &app.settings.options;
    ui.label(
        RichText::new(format!(
            "Preset {}. Keyboard: {}.",
            options.preset.label(),
            options.keyboard.label()
        ))
        .color(theme::TEXT_MUTED),
    );
}

fn status_chips(app: &App, ui: &mut Ui, readiness: Readiness) {
    if matches!(app.gpu, GpuVendor::Unknown) {
        theme::chip(ui, theme::WARN, "GPU not detected");
    } else {
        theme::chip(ui, theme::GOOD, &format!("GPU: {}", app.gpu.label()));
    }
    if app.cache_ready {
        theme::chip(ui, theme::GOOD, "Shader cache filled");
    } else {
        theme::chip(ui, theme::WARN, "Shader cache empty");
    }
    let (color, text) = match readiness {
        Readiness::Ready => (theme::GOOD, "Game folder ready"),
        Readiness::NeedsFolder => (theme::WARN, "No game folder"),
        Readiness::NeedsCheck => (theme::WARN, "Folder not checked"),
        Readiness::Problem => (theme::BAD, "Folder has problems"),
    };
    theme::chip(ui, color, text);
}

/// What the big button does: launch when everything is ready, else go to the step that is not.
fn press_play(app: &mut App, readiness: Readiness) {
    match readiness {
        Readiness::Ready => app.start(false),
        Readiness::NeedsCheck => {
            app.launch_when_ready = true;
            app.start_verify();
        }
        Readiness::NeedsFolder => app.pick_game_folder(),
        Readiness::Problem => app.tab = Tab::Files,
    }
}

fn hero_art(texture: Option<&TextureHandle>, ui: &mut Ui) {
    let side = ui.available_width().min(ART_SIDE);
    let radius = CornerRadius::same(22);
    let rect = match texture {
        Some(texture) => {
            ui.add(
                egui::Image::new(texture)
                    .corner_radius(radius)
                    .fit_to_exact_size(vec2(side, side)),
            )
            .rect
        }
        None => {
            let (rect, _) = ui.allocate_exact_size(vec2(side, side), egui::Sense::hover());
            ui.painter()
                .add(egui::Shape::mesh(theme::gradient_mesh(rect)));
            ui.painter().text(
                rect.center(),
                egui::Align2::CENTER_CENTER,
                "AnyXboxX",
                egui::FontId::proportional(side / 7.0),
                Color32::WHITE,
            );
            rect
        }
    };
    ui.painter().rect_stroke(
        rect,
        radius,
        Stroke::new(1.5_f32, theme::HOT_PINK.gamma_multiply(0.7)),
        egui::StrokeKind::Outside,
    );
}
