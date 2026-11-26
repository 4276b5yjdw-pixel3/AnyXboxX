//! The splash screen: shown for a moment at start-up and while a long job runs. Its picture is
//! never in the repository (it may carry third-party marks); it is read at run time from
//! `ANYXBOXX_LAUNCHER_SPLASH`, else `%LOCALAPPDATA%\AnyXboxX\launcher\splash.png`. Without a
//! picture the gradient and the title "AnyXboxX" are drawn instead. The painting is in
//! `ui_launch`; this module holds the picture, the timing and what the status line says.

use std::ffi::{OsStr, OsString};
use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, Receiver};
use std::time::{Duration, Instant};

use eframe::egui::{self, ColorImage, TextureHandle, TextureOptions};

use crate::progress::Progress;

/// Environment variable that points at the splash picture.
pub const SPLASH_ENV: &str = "ANYXBOXX_LAUNCHER_SPLASH";
/// How long the splash stays at start-up.
pub const STARTUP_DURATION: Duration = Duration::from_millis(2000);
/// The picture is shrunk to this many pixels on its longest side before it becomes a texture.
const MAX_TEXTURE_SIDE: u32 = 2048;

/// The first existing picture among the override and the local folder.
pub fn resolve_path(
    env_value: Option<&OsStr>,
    local_app_data: Option<&OsStr>,
    exists: &dyn Fn(&Path) -> bool,
) -> Option<PathBuf> {
    let from_env = env_value
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
        .filter(|p| exists(p));
    from_env.or_else(|| {
        local_app_data
            .filter(|v| !v.is_empty())
            .map(|root| {
                PathBuf::from(root)
                    .join("AnyXboxX")
                    .join("launcher")
                    .join("splash.png")
            })
            .filter(|p| exists(p))
    })
}

/// The picture path as this machine has it.
pub fn current_path() -> Option<PathBuf> {
    let env_value: Option<OsString> = std::env::var_os(SPLASH_ENV);
    let local = std::env::var_os("LOCALAPPDATA");
    resolve_path(env_value.as_deref(), local.as_deref(), &|p| p.is_file())
}

/// Whether the splash is on screen: at start-up for its duration, then while a job runs unless the
/// user hid it for this job.
pub fn is_visible(elapsed: Duration, job_running: bool, hidden_for_job: bool) -> bool {
    elapsed < STARTUP_DURATION || (job_running && !hidden_for_job)
}

/// The line under the picture: the translate progress, else the last log line, else `idle`.
pub fn status_text(progress: Option<&Progress>, last_line: Option<&str>, idle: &str) -> String {
    if let Some(p) = progress {
        return format!("{} of {} {} ({}%)", p.done, p.total, p.what, p.percent);
    }
    match last_line.map(str::trim).filter(|l| !l.is_empty()) {
        Some(line) => line.chars().take(110).collect(),
        None => idle.to_string(),
    }
}

/// Decodes a PNG into a colour image, shrunk so its longest side is at most `max_side`.
pub fn load_image(path: &Path, max_side: u32) -> Result<ColorImage, String> {
    let decoded = image::open(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let shrunk = if decoded.width().max(decoded.height()) > max_side {
        decoded.resize(max_side, max_side, image::imageops::FilterType::Triangle)
    } else {
        decoded
    };
    let rgba = shrunk.to_rgba8();
    let size = [rgba.width() as usize, rgba.height() as usize];
    Ok(ColorImage::from_rgba_unmultiplied(size, rgba.as_raw()))
}

/// The splash's state: when it started, its picture (loaded on a thread) and the job it was hidden
/// for.
pub struct Splash {
    started: Instant,
    pending: Option<Receiver<Option<ColorImage>>>,
    texture: Option<TextureHandle>,
    hidden_for_job: bool,
    was_running: bool,
}

impl Splash {
    pub fn new() -> Self {
        let (tx, rx) = mpsc::channel();
        std::thread::spawn(move || {
            let image = current_path().and_then(|p| match load_image(&p, MAX_TEXTURE_SIDE) {
                Ok(image) => Some(image),
                Err(error) => {
                    eprintln!("splash picture ignored: {error}");
                    None
                }
            });
            let _ = tx.send(image);
        });
        Splash {
            started: Instant::now(),
            pending: Some(rx),
            texture: None,
            hidden_for_job: false,
            was_running: false,
        }
    }

    /// The picture as a texture, once decoded.
    pub fn texture(&self) -> Option<&TextureHandle> {
        self.texture.as_ref()
    }

    /// Takes the decoded picture when the thread is done.
    pub fn poll(&mut self, ctx: &egui::Context) {
        let Some(rx) = &self.pending else {
            return;
        };
        if let Ok(image) = rx.try_recv() {
            self.texture = image.map(|i| ctx.load_texture("splash", i, TextureOptions::LINEAR));
            self.pending = None;
        }
    }

    /// Whether to draw it this frame; also re-arms it when a new job starts.
    pub fn visible(&mut self, job_running: bool) -> bool {
        if job_running && !self.was_running {
            self.hidden_for_job = false;
        }
        self.was_running = job_running;
        is_visible(self.started.elapsed(), job_running, self.hidden_for_job)
    }

    /// Ends the start-up moment now (a click on the splash).
    pub fn skip_startup(&mut self) {
        self.started -= STARTUP_DURATION;
    }

    /// Hides the launch screen until the next job ("Show details").
    pub fn hide_for_job(&mut self) {
        self.hidden_for_job = true;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn only(paths: &'static [&'static str]) -> impl Fn(&Path) -> bool {
        move |p: &Path| paths.iter().any(|x| Path::new(x) == p)
    }

    #[test]
    fn the_override_comes_first() {
        let exists = |_: &Path| true;
        let got = resolve_path(
            Some(OsStr::new("D:\\mine.png")),
            Some(OsStr::new("C:\\Users\\x\\AppData\\Local")),
            &exists,
        );
        assert_eq!(got, Some(PathBuf::from("D:\\mine.png")));
    }

    #[test]
    fn a_missing_override_falls_back_to_the_local_folder() {
        let local = Path::new("C:\\L")
            .join("AnyXboxX")
            .join("launcher")
            .join("splash.png");
        let local_str: &'static str =
            Box::leak(local.to_string_lossy().into_owned().into_boxed_str());
        let paths: &'static [&'static str] = Box::leak(vec![local_str].into_boxed_slice());
        let got = resolve_path(
            Some(OsStr::new("D:\\gone.png")),
            Some(OsStr::new("C:\\L")),
            &only(paths),
        );
        assert_eq!(got, Some(local));
    }

    #[test]
    fn an_empty_override_is_ignored() {
        let exists = |_: &Path| false;
        assert_eq!(
            resolve_path(Some(OsStr::new("")), Some(OsStr::new("")), &exists),
            None
        );
    }

    #[test]
    fn nothing_found_gives_none() {
        let exists = |_: &Path| false;
        assert_eq!(resolve_path(None, Some(OsStr::new("C:\\L")), &exists), None);
        assert_eq!(resolve_path(None, None, &exists), None);
    }

    #[test]
    fn visibility_follows_startup_then_jobs() {
        let short = Duration::from_millis(500);
        let long = Duration::from_secs(5);
        assert!(is_visible(short, false, false));
        assert!(!is_visible(long, false, false));
        assert!(is_visible(long, true, false));
        assert!(!is_visible(long, true, true));
    }

    #[test]
    fn status_prefers_progress_then_log_then_idle() {
        let p = Progress {
            file: "f".into(),
            done: 3,
            total: 10,
            percent: 30,
            what: "containers".into(),
        };
        assert_eq!(
            status_text(Some(&p), Some("log"), "idle"),
            "3 of 10 containers (30%)"
        );
        assert_eq!(status_text(None, Some("  building  "), "idle"), "building");
        assert_eq!(status_text(None, Some("   "), "idle"), "idle");
        assert_eq!(status_text(None, None, "idle"), "idle");
    }

    #[test]
    fn a_png_is_decoded_and_shrunk() {
        let dir = tempfile::tempdir().expect("temp dir");
        let path = dir.path().join("s.png");
        image::RgbaImage::from_pixel(40, 20, image::Rgba([255, 0, 128, 255]))
            .save(&path)
            .expect("write png");
        let small = load_image(&path, 10).expect("decode");
        assert_eq!(small.size, [10, 5]);
        let full = load_image(&path, 100).expect("decode");
        assert_eq!(full.size, [40, 20]);
        assert!(load_image(&dir.path().join("none.png"), 10).is_err());
    }
}
