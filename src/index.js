import { copyFile, lstat, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import nunjucks from "nunjucks";

const TEMPLATE_SUFFIX = ".j2";
const KEEP_FILE = ".scaffold-keep";
const TEMPLATE_ROOT = fileURLToPath(
  new URL("harmonyos_scaffolder/templates/", import.meta.url),
);

const IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]*$/;
const MODULE_NAME = /^[a-z][A-Za-z0-9_]*$/;
const BUNDLE_NAME = /^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$/;
const CANGJIE_PACKAGE = /^[a-z][a-z0-9_]*$/;
const CJC_VERSION = /^[0-9A-Za-z][0-9A-Za-z._+-]*$/;
const SDK_VERSION = /^\d+\.\d+\.\d+\((\d+)\)$/;
const PERMISSION = /^ohos\.permission\.[A-Za-z][A-Za-z0-9_.]*$/;
const SUPPORTED_DEVICE_TYPES = new Set(["phone", "tablet"]);
const WINDOWS_RESERVED_NAMES = new Set([
  "CON",
  "PRN",
  "AUX",
  "NUL",
  ...Array.from({ length: 9 }, (_, index) => `COM${index + 1}`),
  ...Array.from({ length: 9 }, (_, index) => `LPT${index + 1}`),
]);
const CANGJIE_KEYWORDS = new Set(
  `as abstract break Bool case catch class const continue Rune do else enum extend
   for func false finally foreign Float16 Float32 Float64 if in is init import
   interface Int8 Int16 Int32 Int64 IntNative let main macro match Nothing open
   operator override package private protected public redef return spawn static String
   struct super synchronized this This throw true try type UInt8 UInt16 UInt32 UInt64
   UIntNative Unit unsafe var VArray where while`.split(/\s+/),
);
const ARKTS_KEYWORDS = new Set(
  `await break case catch class const continue debugger default delete do else enum
   export extends false finally for function if import in instanceof let new null
   return super switch this throw true try typeof var void while with yield implements
   interface package private protected public static`.split(/\s+/),
);

export const HostPlatform = Object.freeze({
  AUTO: "auto",
  MACOS_ARM64: "macos-arm64",
  WINDOWS_X64: "windows-x64",
});

const TEMPLATES = Object.freeze([
  Object.freeze({
    name: "cangjie-empty-ability",
    displayName: "Cangjie Empty Ability",
    description: "A stage-model HarmonyOS app whose ability and ArkUI view use Cangjie.",
  }),
  Object.freeze({
    name: "hybrid-cangjie-ability",
    displayName: "Hybrid Cangjie Ability",
    description: "A stage-model ArkTS ability that calls a Cangjie shared library.",
  }),
]);

const DEFAULTS = Object.freeze({
  moduleName: "entry",
  abilityName: "EntryAbility",
  cangjiePackage: undefined,
  viewName: "EntryView",
  backupAbilityName: "EntryBackupAbility",
  vendor: "example",
  targetSdkVersion: "6.1.1(24)",
  compatibleSdkVersion: "6.1.1(24)",
  modelVersion: "6.1.1",
  cjcVersion: "1.1.3",
  appVersionCode: 1_000_000,
  appVersionName: "1.0.0",
  appBuildVersion: "1",
  deviceTypes: ["phone"],
  permissions: [],
  installationFree: false,
  exported: true,
  homeScreen: true,
  hostPlatform: HostPlatform.AUTO,
});
const ALLOWED_OPTIONS = new Set([...Object.keys(DEFAULTS), "projectName", "bundleName", "overwrite"]);

export class ScaffoldError extends Error {
  constructor(message, options) {
    super(message, options);
    this.name = new.target.name;
  }
}

export class ConfigurationError extends ScaffoldError {}
export class TemplateNotFoundError extends ScaffoldError {}
export class DestinationError extends ScaffoldError {}

export function listTemplates() {
  return [...TEMPLATES];
}

export async function scaffold(template, destination, options = {}) {
  if (!TEMPLATES.some((item) => item.name === template)) {
    const choices = TEMPLATES.map((item) => item.name).join(", ");
    throw new TemplateNotFoundError(
      `unknown template ${JSON.stringify(template)}; available choices: ${choices}`,
    );
  }
  if (typeof destination !== "string" || destination.length === 0) {
    throw new DestinationError("destination must be a non-empty path string");
  }
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new ConfigurationError("options must be an object");
  }
  const unknownOptions = Object.keys(options).filter((name) => !ALLOWED_OPTIONS.has(name));
  if (unknownOptions.length > 0) {
    throw new ConfigurationError(`unknown option: ${unknownOptions.join(", ")}`);
  }

  const { overwrite = false, ...configOptions } = options;
  if (typeof overwrite !== "boolean") {
    throw new ConfigurationError("overwrite must be a boolean");
  }

  const destinationPath = path.resolve(destination);
  const destinationStat = await optionalLstat(destinationPath);
  if (destinationStat && !destinationStat.isDirectory()) {
    throw new DestinationError(`destination is not a directory: ${destinationPath}`);
  }
  if (destinationStat && !overwrite && (await readdir(destinationPath)).length > 0) {
    throw new DestinationError(
      `destination is not empty: ${destinationPath}; pass overwrite: true to merge generated files`,
    );
  }

  const context = createTemplateContext(configOptions);
  const environment = new nunjucks.Environment(undefined, {
    autoescape: false,
    lstripBlocks: true,
    throwOnUndefined: true,
    trimBlocks: true,
  });
  environment.addFilter("json", (value) => JSON.stringify(value));

  const sourceRoot = path.join(TEMPLATE_ROOT, template, "project");
  await renderDirectory(sourceRoot, destinationPath, environment, context);
}

function createTemplateContext(options) {
  const config = { ...DEFAULTS, ...options };
  if (config.cangjiePackage === undefined || config.cangjiePackage === null) {
    config.cangjiePackage = `ohos_app_cangjie_${config.moduleName}`;
  }

  requireString(config.projectName, "projectName");
  if (config.projectName.trim() === "") {
    throw new ConfigurationError("projectName must not be empty");
  }
  if (/[\r\n\0]/.test(config.projectName)) {
    throw new ConfigurationError("projectName must not contain control characters");
  }
  requireString(config.bundleName, "bundleName");
  if (!BUNDLE_NAME.test(config.bundleName)) {
    throw new ConfigurationError(
      "bundleName must contain at least two dot-separated identifier segments",
    );
  }
  requireMatchingString(config.moduleName, "moduleName", MODULE_NAME,
    "must start with a lowercase letter and contain only letters, digits, and underscores");
  validatePathName(config.moduleName, "moduleName");

  for (const field of ["abilityName", "viewName", "backupAbilityName"]) {
    requireMatchingString(config[field], field, IDENTIFIER, "must be a valid source identifier");
  }
  if (CANGJIE_KEYWORDS.has(config.viewName)) {
    throw new ConfigurationError("viewName must not be a Cangjie keyword");
  }
  for (const field of ["abilityName", "backupAbilityName"]) {
    if (ARKTS_KEYWORDS.has(config[field])) {
      throw new ConfigurationError(`${field} must not be an ArkTS keyword`);
    }
    validatePathName(config[field], field);
  }
  if (config.abilityName.toLowerCase() === config.backupAbilityName.toLowerCase()) {
    throw new ConfigurationError(
      "abilityName and backupAbilityName must differ when compared case-insensitively",
    );
  }
  requireMatchingString(config.cangjiePackage, "cangjiePackage", CANGJIE_PACKAGE,
    "must start with a lowercase letter and contain only lowercase letters, digits, and underscores");
  if (CANGJIE_KEYWORDS.has(config.cangjiePackage)) {
    throw new ConfigurationError("cangjiePackage must not be a Cangjie keyword");
  }
  validatePathName(config.cangjiePackage, "cangjiePackage");

  requireString(config.vendor, "vendor");
  if (config.vendor.trim() === "" || /[\r\n\0]/.test(config.vendor)) {
    throw new ConfigurationError("vendor must be a non-empty single-line value");
  }
  for (const field of ["modelVersion", "appVersionName", "appBuildVersion"]) {
    requireString(config[field], field);
    if (config[field] === "" || /["\r\n\0]/.test(config[field])) {
      throw new ConfigurationError(`${field} must be a non-empty quoted-string value`);
    }
  }
  requireMatchingString(config.cjcVersion, "cjcVersion", CJC_VERSION,
    "may contain only letters, digits, dots, underscores, pluses, and hyphens");

  const targetApi = parseSdkApi(config.targetSdkVersion, "targetSdkVersion");
  const compatibleApi = parseSdkApi(config.compatibleSdkVersion, "compatibleSdkVersion");
  if (compatibleApi < 22) {
    throw new ConfigurationError("compatibleSdkVersion must use API 22 or newer");
  }
  if (targetApi < compatibleApi) {
    throw new ConfigurationError(
      "targetSdkVersion API must be greater than or equal to compatibleSdkVersion API",
    );
  }
  if (!Number.isInteger(config.appVersionCode) || config.appVersionCode < 1) {
    throw new ConfigurationError("appVersionCode must be a positive integer");
  }
  for (const field of ["installationFree", "exported", "homeScreen"]) {
    if (typeof config[field] !== "boolean") {
      throw new ConfigurationError(`${field} must be a boolean`);
    }
  }
  if (config.homeScreen && !config.exported) {
    throw new ConfigurationError("homeScreen requires exported: true");
  }

  validateStringArray(config.deviceTypes, "deviceTypes");
  if (config.deviceTypes.length === 0) {
    throw new ConfigurationError("deviceTypes must contain at least one device type");
  }
  const unsupported = config.deviceTypes.filter((item) => !SUPPORTED_DEVICE_TYPES.has(item));
  if (unsupported.length > 0) {
    throw new ConfigurationError("deviceTypes only supports: phone, tablet");
  }
  rejectDuplicates(config.deviceTypes, "deviceTypes");

  validateStringArray(config.permissions, "permissions");
  if (config.permissions.some((permission) => !PERMISSION.test(permission))) {
    throw new ConfigurationError(
      "permissions must use the form ohos.permission.PERMISSION_NAME",
    );
  }
  rejectDuplicates(config.permissions, "permissions");

  config.hostPlatform = resolveHostPlatform(config.hostPlatform);
  return {
    project_name: config.projectName,
    bundle_name: config.bundleName,
    module_name: config.moduleName,
    ability_name: config.abilityName,
    cangjie_package: config.cangjiePackage,
    view_name: config.viewName,
    backup_ability_name: config.backupAbilityName,
    vendor: config.vendor,
    target_sdk_version: config.targetSdkVersion,
    compatible_sdk_version: config.compatibleSdkVersion,
    model_version: config.modelVersion,
    cjc_version: config.cjcVersion,
    app_version_code: config.appVersionCode,
    app_version_name: config.appVersionName,
    app_build_version: config.appBuildVersion,
    device_types: [...config.deviceTypes],
    permissions: [...config.permissions],
    installation_free: config.installationFree,
    exported: config.exported,
    home_screen: config.homeScreen,
    host_platform: config.hostPlatform,
    module_name_upper: config.moduleName.toUpperCase(),
    ability_name_lower: config.abilityName.toLowerCase(),
    backup_ability_name_lower: config.backupAbilityName.toLowerCase(),
  };
}

async function renderDirectory(source, destination, environment, context) {
  const destinationStat = await optionalLstat(destination);
  if (destinationStat && !destinationStat.isDirectory()) {
    throw new DestinationError(`cannot replace non-directory with generated directory: ${destination}`);
  }
  try {
    await mkdir(destination, { recursive: true });
  } catch (error) {
    throw new DestinationError(`cannot create generated directory: ${destination}`, {
      cause: error,
    });
  }

  const entries = await readdir(source, { withFileTypes: true });
  const outputs = new Set();
  for (const entry of entries) {
    if (entry.isFile() && entry.name === KEEP_FILE) {
      continue;
    }
    const renderedName = renderPathSegment(entry.name, environment, context);
    const outputName = entry.isFile() && renderedName.endsWith(TEMPLATE_SUFFIX)
      ? renderedName.slice(0, -TEMPLATE_SUFFIX.length)
      : renderedName;
    if (outputs.has(outputName)) {
      throw new ScaffoldError(`template renders duplicate path: ${path.join(destination, outputName)}`);
    }
    outputs.add(outputName);

    const sourcePath = path.join(source, entry.name);
    const outputPath = path.join(destination, outputName);
    if (entry.isDirectory()) {
      await renderDirectory(sourcePath, outputPath, environment, context);
    } else if (entry.isFile()) {
      const outputStat = await optionalLstat(outputPath);
      if (outputStat?.isDirectory()) {
        throw new DestinationError(`cannot replace directory with generated file: ${outputPath}`);
      }
      if (outputStat && !outputStat.isFile()) {
        throw new DestinationError(`cannot replace non-file with generated file: ${outputPath}`);
      }
      if (renderedName.endsWith(TEMPLATE_SUFFIX)) {
        const template = await readFile(sourcePath, "utf8");
        let rendered;
        try {
          rendered = environment.renderString(template, context);
        } catch (error) {
          throw new ScaffoldError(`failed to render template ${entry.name}: ${error.message}`, {
            cause: error,
          });
        }
        await writeFile(outputPath, rendered, "utf8");
      } else {
        await copyFile(sourcePath, outputPath);
      }
    }
  }
}

function renderPathSegment(sourceName, environment, context) {
  let value;
  try {
    value = environment.renderString(sourceName, context);
  } catch (error) {
    throw new ScaffoldError(`failed to render template path ${JSON.stringify(sourceName)}: ${error.message}`, {
      cause: error,
    });
  }
  if (!value || value === "." || value === ".." || /[/\\\0]/.test(value)) {
    throw new ScaffoldError(
      `template path segment ${JSON.stringify(sourceName)} rendered to unsafe value ${JSON.stringify(value)}`,
    );
  }
  return value;
}

async function optionalLstat(filePath) {
  try {
    return await lstat(filePath);
  } catch (error) {
    if (error.code === "ENOENT") {
      return undefined;
    }
    throw error;
  }
}

function requireString(value, field) {
  if (typeof value !== "string") {
    throw new ConfigurationError(`${field} must be a string`);
  }
}

function requireMatchingString(value, field, pattern, message) {
  requireString(value, field);
  if (!pattern.test(value)) {
    throw new ConfigurationError(`${field} ${message}`);
  }
}

function validatePathName(value, field) {
  if (WINDOWS_RESERVED_NAMES.has(value.toUpperCase())) {
    throw new ConfigurationError(`${field} must not be a Windows-reserved path name`);
  }
}

function parseSdkApi(value, field) {
  requireString(value, field);
  const match = SDK_VERSION.exec(value);
  if (!match) {
    throw new ConfigurationError(`${field} must use the format major.minor.patch(api)`);
  }
  return Number(match[1]);
}

function validateStringArray(value, field) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new ConfigurationError(`${field} must be an array of strings`);
  }
}

function rejectDuplicates(value, field) {
  if (new Set(value).size !== value.length) {
    throw new ConfigurationError(`${field} must not contain duplicates`);
  }
}

function resolveHostPlatform(hostPlatform) {
  if (!Object.values(HostPlatform).includes(hostPlatform)) {
    throw new ConfigurationError(
      `hostPlatform must be one of: ${Object.values(HostPlatform).join(", ")}`,
    );
  }
  if (hostPlatform !== HostPlatform.AUTO) {
    return hostPlatform;
  }
  if (process.platform === "win32") {
    return HostPlatform.WINDOWS_X64;
  }
  if (process.platform === "darwin" && process.arch === "arm64") {
    return HostPlatform.MACOS_ARM64;
  }
  throw new ConfigurationError(
    "hostPlatform could not be detected as windows-x64 or macos-arm64; pass it explicitly for the machine that will build the project",
  );
}
