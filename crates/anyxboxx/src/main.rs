//! `anyxboxx`: AnyXboxX's command line in Rust (docs/architecture-rust.md).
//!
//! `anyxboxx run --game-dir <folder> [...]` replaces the former `tools/lancer_victory.ps1`;
//! `anyxboxx rapport <target>` replaces `scarlett.py --rapport`;
//! `anyxboxx traduction <package> [image.svg]` replaces `scarlett.py --traduction`.

use std::process::ExitCode;

use anyxboxx::{rapport, run, traduction};
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "anyxboxx",
    version,
    about = "AnyXboxX: run Xbox Series executables on Windows"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Build VIctory and launch it on your own game folder (replaces the former tools/lancer_victory.ps1).
    Run(run::RunArgs),
    /// Compatibility report of an executable or package folder (replaces scarlett.py --rapport).
    Rapport(rapport::RapportArgs),
    /// Translation progress of the console DLLs, and its SVG image (replaces scarlett.py --traduction).
    Traduction(traduction::TraductionArgs),
}

fn main() -> ExitCode {
    match Cli::parse().command {
        Command::Run(args) => launch(&args),
        Command::Rapport(args) => match rapport::rapport(&args) {
            Ok(text) => {
                println!("{text}");
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("anyxboxx rapport: {error}");
                ExitCode::FAILURE
            }
        },
        Command::Traduction(args) => report("traduction", traduction::traduction(&args)),
    }
}

/// Exit code of a report command; its error goes to stderr after `anyxboxx <command>: `.
fn report<E: std::fmt::Display>(command: &str, outcome: Result<(), E>) -> ExitCode {
    match outcome {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("anyxboxx {command}: {error}");
            ExitCode::FAILURE
        }
    }
}

fn launch(args: &run::RunArgs) -> ExitCode {
    let Some(repo) = run::find_repo(args.repo.as_deref()) else {
        eprintln!("anyxboxx run: repository not found (pass --repo or set ANYXBOXX_REPO).");
        return ExitCode::FAILURE;
    };
    match run::run(args, &repo) {
        // VIctory's exit code passed on whole (a crash code such as 0xC0000005 included).
        Ok(code) => std::process::exit(code),
        Err(error) => {
            eprintln!("anyxboxx run: {error}");
            ExitCode::FAILURE
        }
    }
}
