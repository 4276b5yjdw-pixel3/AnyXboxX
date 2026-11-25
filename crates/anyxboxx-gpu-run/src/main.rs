mod adapter;
mod gpu;

use std::{ffi::OsString, fs, path::Path};

fn fail(message: &str) -> i32 {
    eprintln!("[gpu] {message} (0x80004005)");
    1
}
fn number(value: &OsString) -> u32 {
    value.to_string_lossy().trim().parse::<i32>().unwrap_or(0) as u32
}
fn read(path: &OsString) -> std::io::Result<Vec<u8>> {
    fs::read(Path::new(path))
}

fn run(args: &[OsString], draw: bool) -> i32 {
    if draw && args.len() < 8 {
        return fail("--draw <vs.dxil> <ps.dxil|-> <mémoire.bin> <sommets> <largeur> <hauteur>");
    }
    let memory_index = if draw { 4 } else { 2 };
    let shader = read(&args[if draw { 2 } else { 1 }]);
    let pixel = draw && args[3] != "-";
    let ps = if pixel {
        read(&args[3])
    } else {
        Ok(Vec::new())
    };
    let memory = read(&args[memory_index]);
    let (Ok(shader), Ok(ps), Ok(mut memory)) = (shader, ps, memory) else {
        return fail("lecture des fichiers impossible");
    };
    let original = memory.len();
    memory.resize(original.div_ceil(4) * 4 + 4, 0);
    let spec = if draw {
        Some(gpu::Draw {
            vertices: number(&args[5]),
            width: number(&args[6]),
            height: number(&args[7]),
            pixel,
        })
    } else {
        None
    };
    if spec
        .as_ref()
        .is_some_and(|d| d.vertices == 0 || d.width == 0 || d.height == 0)
    {
        return fail("sommets, largeur et hauteur > 0");
    }
    let groups = if !draw && args.len() > 3 {
        number(&args[3])
    } else {
        1
    };
    let Ok((_, device, kind)) = adapter::chosen() else {
        return fail("aucun périphérique D3D12");
    };
    let pipeline = gpu::root(&device).and_then(|root| {
        let pipeline = if draw {
            gpu::graphics(&device, &root, &shader, &ps)
        } else {
            gpu::compute(&device, &root, &shader)
        }?;
        Ok((root, pipeline))
    });
    let Ok((root, pipeline)) = pipeline else {
        return fail(if draw {
            "VS/PS DXIL refusés (signature ou format)"
        } else {
            "shader DXIL refusé (signature ou format)"
        });
    };
    if gpu::execute(
        &device,
        &root,
        &pipeline,
        &mut memory,
        groups,
        spec.as_ref(),
    )
    .is_err()
    {
        return fail("exécution GPU impossible");
    }
    if fs::write(Path::new(&args[memory_index]), &memory[..original]).is_err() {
        return fail("écriture du résultat impossible");
    }
    if let Some(d) = spec {
        println!(
            "[gpu] {kind} : {} sommet(s) dessiné(s) sur {}x{}",
            d.vertices, d.width, d.height
        );
    } else {
        println!("[gpu] {kind} : {groups} groupe(s) exécuté(s)");
    }
    0
}
fn main() {
    let args: Vec<_> = std::env::args_os().collect();
    let status = if args.get(1).is_some_and(|s| s == "--adaptateur") {
        if adapter::print_adapter().is_ok() {
            0
        } else {
            1
        }
    } else if args.get(1).is_some_and(|s| s == "--draw") {
        run(&args, true)
    } else if args.len() < 3 {
        eprintln!(
            "Usage : anyxboxx_gpu_run.exe <shader.dxil> <mémoire.bin> [groupes]\n        anyxboxx_gpu_run.exe --draw <vs.dxil> <ps.dxil|-> <mémoire.bin> <sommets> <largeur> <hauteur>\n        anyxboxx_gpu_run.exe --adaptateur"
        );
        2
    } else {
        run(&args, false)
    };
    std::process::exit(status);
}
