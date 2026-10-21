//! The controlled fork's legacy installer must refuse before downloading or replacing any binary.
#![cfg(unix)]

use std::{fs, os::unix::fs::PermissionsExt, path::Path, process::Command};

fn refuses_install(existing: bool) {
    let root = std::env::temp_dir().join(format!("rn-controlled-install-{existing}-{}", std::process::id()));
    let fake = root.join("fake");
    let bin = root.join("bin");
    fs::create_dir_all(&fake).unwrap();
    fs::create_dir_all(&bin).unwrap();
    let marker = root.join("download-attempted");
    let curl = fake.join("curl");
    fs::write(&curl, "#!/bin/sh\ntouch \"$REASON_TEST_MARKER\"\nexit 1\n").unwrap();
    fs::set_permissions(&curl, fs::Permissions::from_mode(0o755)).unwrap();
    let binary = bin.join("reason-network");
    if existing {
        fs::write(&binary, b"reviewed binary must remain unchanged").unwrap();
    }
    let out = Command::new("sh")
        .arg(Path::new(env!("CARGO_MANIFEST_DIR")).join("install.sh"))
        .env("PATH", format!("{}:{}", fake.display(), std::env::var("PATH").unwrap()))
        .env("REASON_NETWORK_BIN_DIR", &bin)
        .env("REASON_NETWORK_DOWNLOAD_BASE", "https://example.invalid/forbidden")
        .env("REASON_NETWORK_NO_PROMPT", "1")
        .env("REASON_TEST_MARKER", &marker)
        .output()
        .unwrap();
    assert!(!out.status.success());
    assert!(String::from_utf8_lossy(&out.stderr).contains("remote binary installation is disabled"));
    assert!(!marker.exists(), "installer attempted a download");
    if existing {
        assert_eq!(fs::read(&binary).unwrap(), b"reviewed binary must remain unchanged");
    } else {
        assert!(!binary.exists(), "installer created a binary");
    }
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn remote_installer_cannot_replace_an_existing_binary() {
    refuses_install(true);
}

#[test]
fn remote_installer_cannot_create_a_new_installation() {
    refuses_install(false);
}
