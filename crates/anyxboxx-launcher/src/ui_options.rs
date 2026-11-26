//! The "Launch options" card grid of the Play page. The choices are plain data in `options`; the
//! settings file keeps them between runs.

use eframe::egui::{self, RichText, Ui};

use crate::app::App;
use crate::options::{Keyboard, LogLevel, Preset, Resolution, WindowMode};
use crate::theme;

pub fn cards(app: &mut App, ui: &mut Ui) {
    ui.label(RichText::new("Launch options").size(22.0).strong());
    ui.add_space(theme::SP_S);
    ui.columns(2, |columns| {
        display_card(app, &mut columns[0]);
        keyboard_card(app, &mut columns[1]);
    });
    ui.add_space(theme::SP_S);
    ui.columns(2, |columns| {
        performance_card(app, &mut columns[0]);
        diagnostics_card(app, &mut columns[1]);
    });
}

fn card_title(ui: &mut Ui, text: &str) {
    ui.label(RichText::new(text).size(18.0).strong());
    ui.add_space(theme::SP_XS);
}

/// One pill per choice; the chosen one is lit.
fn pills<T: Copy + PartialEq>(
    ui: &mut Ui,
    value: &mut T,
    all: &[T],
    label: impl Fn(T) -> &'static str,
) {
    ui.horizontal_wrapped(|ui| {
        for &choice in all {
            if theme::tab_pill(ui, *value == choice, label(choice)) {
                *value = choice;
            }
        }
    });
}

fn toggle_row(ui: &mut Ui, text: &str, value: &mut bool) {
    ui.horizontal(|ui| {
        theme::toggle(ui, value);
        ui.label(text);
    });
}

fn display_card(app: &mut App, ui: &mut Ui) {
    theme::card(ui, |ui| {
        card_title(ui, "Display");
        let options = &mut app.settings.options;
        pills(
            ui,
            &mut options.resolution,
            &Resolution::ALL,
            Resolution::label,
        );
        if options.resolution == Resolution::Custom {
            ui.horizontal(|ui| {
                ui.add(egui::DragValue::new(&mut options.custom_width).range(0..=9999));
                ui.label("x");
                ui.add(egui::DragValue::new(&mut options.custom_height).range(0..=9999));
            });
            if !options.custom_valid() {
                ui.colored_label(
                    theme::WARN,
                    "VIctory takes 640x360 to 7680x4320; outside that it uses 3840x2160.",
                );
            }
        }
        ui.add_space(theme::SP_S);
        pills(ui, &mut options.window, &WindowMode::ALL, WindowMode::label);
        ui.label(
            RichText::new("The size is what the console reports to the game.")
                .color(theme::TEXT_MUTED),
        );
    });
}

fn keyboard_card(app: &mut App, ui: &mut Ui) {
    theme::card(ui, |ui| {
        card_title(ui, "Keyboard");
        let keyboard = &mut app.settings.options.keyboard;
        pills(ui, keyboard, &Keyboard::ALL, Keyboard::label);
        ui.add_space(theme::SP_S);
        ui.label(format!("Move: {}", keyboard.move_keys()));
        ui.label("Look: I J K L (up, left, down, right)");
        ui.label(keyboard.shoulder_keys());
        ui.label("Confirm: Enter. Back: Backspace. Menu: Esc.");
    });
}

fn performance_card(app: &mut App, ui: &mut Ui) {
    theme::card(ui, |ui| {
        card_title(ui, "Performance");
        let settings = &mut app.settings;
        pills(
            ui,
            &mut settings.options.preset,
            &Preset::ALL,
            Preset::label,
        );
        ui.label(RichText::new(settings.options.preset.description()).color(theme::TEXT_MUTED));
        ui.add_space(theme::SP_S);
        ui.add(
            egui::Slider::new(&mut settings.jobs, 0..=32).text("shader workers (0 = every core)"),
        );
        toggle_row(
            ui,
            "Warm the shaders before the game starts",
            &mut settings.options.warm_first,
        );
    });
}

fn diagnostics_card(app: &mut App, ui: &mut Ui) {
    theme::card(ui, |ui| {
        card_title(ui, "Diagnostics");
        let settings = &mut app.settings;
        ui.label("Log level of VIctory");
        pills(
            ui,
            &mut settings.options.log,
            &LogLevel::ALL,
            LogLevel::label,
        );
        ui.add_space(theme::SP_S);
        toggle_row(
            ui,
            "Skip the running-game check",
            &mut settings.skip_process_check,
        );
        ui.label(
            RichText::new("Only if you are sure no game runs (hosts without tasklist).")
                .color(theme::TEXT_MUTED),
        );
    });
}
