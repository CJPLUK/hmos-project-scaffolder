import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, readdir, rm, symlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  ConfigurationError,
  DestinationError,
  HostPlatform,
  TemplateNotFoundError,
  listTemplates,
  scaffold,
} from "../src/index.js";

async function temporaryDirectory(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), "harmonyos-scaffolder-test-"));
  t.after(() => rm(directory, { force: true, recursive: true }));
  return directory;
}

async function allFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.isFile()) {
      files.push(entry.name);
    } else if (entry.isDirectory()) {
      files.push(...await allFiles(path.join(directory, entry.name)));
    }
  }
  return files;
}

test("lists both bundled templates", () => {
  assert.deepEqual(
    listTemplates().map((template) => template.name),
    ["cangjie-empty-ability", "hybrid-cangjie-ability"],
  );
});

test("scaffolds the Cangjie empty ability template", async (t) => {
  const root = await temporaryDirectory(t);
  const destination = path.join(root, "MyApplication");

  await scaffold("cangjie-empty-ability", destination, {
    projectName: "MyApplication",
    bundleName: "com.example.myapplication",
    hostPlatform: HostPlatform.MACOS_ARM64,
  });

  assert.deepEqual(await readdir(path.join(destination, "entry", "libs")), []);
  assert.deepEqual(
    await readdir(path.join(destination, "entry", "src", "main", "resources", "rawfile")),
    [],
  );
  assert.equal((await allFiles(destination)).some((name) => name.endsWith(".j2")), false);
  assert.equal((await allFiles(destination)).includes(".scaffold-keep"), false);
  assert.match(await readFile(path.join(destination, ".gitignore"), "utf8"), /node_modules/);
  assert.match(await readFile(path.join(destination, "entry", ".gitignore"), "utf8"), /oh_modules/);

  const app = JSON.parse(await readFile(path.join(destination, "AppScope", "app.json5"), "utf8"));
  assert.equal(app.app.bundleName, "com.example.myapplication");

  const module = JSON.parse(
    await readFile(path.join(destination, "entry", "src", "main", "module.json5"), "utf8"),
  );
  assert.equal(module.module.name, "entry");
  assert.equal(module.module.mainElement, "EntryAbility");
  assert.deepEqual(module.module.deviceTypes, ["phone"]);
  assert.equal(module.module.srcEntry, "ohos_app_cangjie_entry.MyAbilityStage");
  assert.equal(module.module.requestPermissions, undefined);

  const source = await readFile(
    path.join(destination, "entry", "src", "main", "cangjie", "index.cj"),
    "utf8",
  );
  assert.match(source, /package ohos_app_cangjie_entry/);
  assert.match(source, /class EntryView/);

  const manifest = await readFile(path.join(destination, "entry", "cjpm.toml"), "utf8");
  assert.match(manifest, /\$\{COMPILE_CONDITION_ENTRY\}/);
  assert.match(manifest, /\[target\.aarch64-apple-darwin\]/);
  assert.doesNotMatch(manifest, /x86_64-w64-mingw32/);
});

test("scaffolds the hybrid template with custom paths and permissions", async (t) => {
  const root = await temporaryDirectory(t);
  const destination = path.join(root, "Hybrid");

  await scaffold("hybrid-cangjie-ability", destination, {
    projectName: "Hybrid",
    bundleName: "org.example.hybrid",
    moduleName: "sample",
    abilityName: "SampleAbility",
    cangjiePackage: "sample_cangjie",
    backupAbilityName: "SampleBackup",
    deviceTypes: ["phone", "tablet"],
    permissions: ["ohos.permission.INTERNET", "ohos.permission.PRIVACY_WINDOW"],
    hostPlatform: HostPlatform.WINDOWS_X64,
  });

  const moduleRoot = path.join(destination, "sample");
  await readFile(path.join(moduleRoot, "src", "main", "ets", "sampleability", "SampleAbility.ets"));
  await readFile(path.join(moduleRoot, "src", "main", "ets", "samplebackup", "SampleBackup.ets"));
  await readFile(
    path.join(moduleRoot, "src", "main", "cangjie", "types", "libsample_cangjie", "Index.d.ts"),
  );

  const module = JSON.parse(
    await readFile(path.join(moduleRoot, "src", "main", "module.json5"), "utf8"),
  );
  assert.deepEqual(module.module.deviceTypes, ["phone", "tablet"]);
  assert.deepEqual(module.module.requestPermissions, [
    { name: "ohos.permission.INTERNET" },
    { name: "ohos.permission.PRIVACY_WINDOW" },
  ]);
  assert.equal(module.module.abilities[0].srcEntry, "./ets/sampleability/SampleAbility.ets");
  assert.equal(module.module.extensionAbilities[0].name, "SampleBackup");

  const packageManifest = JSON.parse(
    await readFile(path.join(moduleRoot, "oh-package.json5"), "utf8"),
  );
  assert.deepEqual(packageManifest.dependencies, {
    "libsample_cangjie.so": "file:src/main/cangjie/types/libsample_cangjie",
  });

  const page = await readFile(path.join(moduleRoot, "src", "main", "ets", "pages", "Index.ets"), "utf8");
  assert.match(page, /import \{ testCJ \} from 'libsample_cangjie\.so';/);
  const manifest = await readFile(path.join(moduleRoot, "cjpm.toml"), "utf8");
  assert.match(manifest, /\[target\.x86_64-w64-mingw32\.bin-dependencies\]/);
  assert.doesNotMatch(manifest, /\[target\.aarch64-apple-darwin\]/);
});

test("rejects non-empty destinations unless overwrite is enabled", async (t) => {
  const root = await temporaryDirectory(t);
  const destination = path.join(root, "existing");
  await mkdir(destination);
  const marker = path.join(destination, "user-file.txt");
  await writeFile(marker, "keep me");
  const options = {
    projectName: "Demo",
    bundleName: "com.example.demo",
    hostPlatform: HostPlatform.MACOS_ARM64,
  };

  await assert.rejects(
    scaffold("cangjie-empty-ability", destination, options),
    DestinationError,
  );
  await scaffold("cangjie-empty-ability", destination, { ...options, overwrite: true });

  assert.equal(await readFile(marker, "utf8"), "keep me");
});

test("rejects unknown templates and invalid permissions", async (t) => {
  const root = await temporaryDirectory(t);
  const options = {
    projectName: "Demo",
    bundleName: "com.example.demo",
    hostPlatform: HostPlatform.MACOS_ARM64,
  };

  await assert.rejects(scaffold("missing", path.join(root, "missing"), options), TemplateNotFoundError);
  await assert.rejects(
    scaffold("cangjie-empty-ability", path.join(root, "invalid"), {
      ...options,
      permissions: ["android.permission.INTERNET"],
    }),
    ConfigurationError,
  );
  await assert.rejects(
    scaffold("cangjie-empty-ability", path.join(root, "typo"), {
      ...options,
      installation_free: true,
    }),
    /unknown option: installation_free/,
  );
});

test("overwrite does not follow destination symlinks", { skip: process.platform === "win32" }, async (t) => {
  const root = await temporaryDirectory(t);
  const destination = path.join(root, "destination");
  const outside = path.join(root, "outside");
  await mkdir(destination);
  await mkdir(outside);
  await symlink(outside, path.join(destination, "entry"), "dir");

  await assert.rejects(
    scaffold("cangjie-empty-ability", destination, {
      projectName: "Demo",
      bundleName: "com.example.demo",
      hostPlatform: HostPlatform.MACOS_ARM64,
      overwrite: true,
    }),
    DestinationError,
  );
  assert.deepEqual(await readdir(outside), []);
});
