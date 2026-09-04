export type TemplateName = "cangjie-empty-ability" | "hybrid-cangjie-ability";
export type HostPlatformValue = "auto" | "macos-arm64" | "windows-x64";
export type DeviceType = "phone" | "tablet";

export interface TemplateInfo {
  readonly name: TemplateName;
  readonly displayName: string;
  readonly description: string;
}

export interface ScaffoldOptions {
  projectName: string;
  bundleName: string;
  moduleName?: string;
  abilityName?: string;
  cangjiePackage?: string;
  viewName?: string;
  backupAbilityName?: string;
  vendor?: string;
  targetSdkVersion?: string;
  compatibleSdkVersion?: string;
  modelVersion?: string;
  cjcVersion?: string;
  appVersionCode?: number;
  appVersionName?: string;
  appBuildVersion?: string;
  deviceTypes?: DeviceType[];
  permissions?: string[];
  installationFree?: boolean;
  exported?: boolean;
  homeScreen?: boolean;
  hostPlatform?: HostPlatformValue;
  overwrite?: boolean;
}

export const HostPlatform: Readonly<{
  AUTO: "auto";
  MACOS_ARM64: "macos-arm64";
  WINDOWS_X64: "windows-x64";
}>;

export class ScaffoldError extends Error {}
export class ConfigurationError extends ScaffoldError {}
export class TemplateNotFoundError extends ScaffoldError {}
export class DestinationError extends ScaffoldError {}

export function listTemplates(): TemplateInfo[];

export function scaffold(
  template: TemplateName,
  destination: string,
  options: ScaffoldOptions,
): Promise<void>;
