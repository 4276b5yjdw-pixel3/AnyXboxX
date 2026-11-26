//! The window: the tab bar, the shared log view and the `eframe` hooks. The pages are in
//! `ui_pages`; every decision lives in the other modules.

use std::time::Duration;

use eframe::egui::{self, RichText};

use crate::app::{App, Tab};
use crate::progress::Progress;
use crate::{splash, theme, ui_pages};

/// How often the window redraws while a job or a folder check runs.
const BUSY_REPAINT: Duration = Duration::from_millis(200);

impl eframe::App for App {
    fn logic(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll();
        if self.is_busy() {
            ctx.request_repaint_after(BUSY_REPAINT);
        }
    }

    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        theme::paint_background(&ctx);
        let open_frame = egui::Frame::new().inner_margin(egui::Margin::symmetric(20, 10));
        egui::Panel::top("tabs")
            .frame(open_frame)
            .show_inside(ui, |ui| {
                ui.horizontal(|ui| {
                    ui.label(RichText::new("AnyXboxX").size(26.0).strong());
                    ui.add_space(14.0);
                    for (tab, label) in [
                        (Tab::Setup, "Setup"),
                        (Tab::Files, "Game folder"),
                        (Tab::Shaders, "Shaders"),
                        (Tab::Play, "Play"),
                    ] {
                        if theme::tab_pill(ui, self.tab == tab, label) {
                            self.tab = tab;
                        }
                    }
                });
            });
        if let Some(notice) = self.notice.clone() {
            egui::Panel::bottom("notice")
                .frame(open_frame)
                .show_inside(ui, |ui| {
                    theme::card(ui, |ui| {
                        ui.horizontal(|ui| {
                            ui.label(notice);
                            if ui.small_button("dismiss").clicked() {
                                self.notice = None;
                            }
                        });
                    });
                });
        }
        egui::CentralPanel::default()
            .frame(open_frame)
            .show_inside(ui, |ui| {
                egui::ScrollArea::vertical().show(ui, |ui| match self.tab {
                    Tab::Setup => ui_pages::setup(self, ui),
                    tab => theme::card(ui, |ui| match tab {
                        Tab::Files => ui_pages::files(self, ui),
                        Tab::Shaders => ui_pages::shaders(self, ui),
                        _ => ui_pages::play(self, ui),
                    }),
                });
            });
        ui_pages::confirm_clean(self, &ctx);
        self.show_splash(&ctx);
    }
}

impl App {
    /// The splash over the window at start-up and while a job runs.
    fn show_splash(&mut self, ctx: &egui::Context) {
        let busy = self.running.is_some();
        if !self.splash.visible(busy) {
            return;
        }
        let progress = self.progress().cloned();
        let idle = if busy { "Working..." } else { "Starting..." };
        let status =
            splash::status_text(progress.as_ref(), self.log.back().map(String::as_str), idle);
        let fraction = progress
            .as_ref()
            .map(Progress::fraction)
            .or(busy.then_some(0.0));
        self.splash.show(ctx, busy, &status, fraction);
    }
}

/// The log of VIctory and of the launcher's steps, newest at the bottom.
pub fn log_view(app: &App, ui: &mut egui::Ui) {
    ui.separator();
    ui.label(RichText::new("Log").strong().size(17.0));
    egui::ScrollArea::vertical()
        .id_salt("log")
        .max_height(260.0)
        .stick_to_bottom(true)
        .auto_shrink([false, false])
        .show(ui, |ui| {
            for line in &app.log {
                ui.monospace(line);
            }
        });
}
