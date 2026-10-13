// Export data and reachable assets without importing another gameplay implementation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const project = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const outputIndex = args.indexOf('--output');
if (outputIndex < 0 || !args[outputIndex + 1]) throw new Error('--output is required');
const output = path.resolve(args[outputIndex + 1]);
const catalogOnly = args.includes('--catalog-only');
const read = name => JSON.parse(fs.readFileSync(inside(project, name), 'utf8'));

function inside(root, relative) {
  const absolute = path.resolve(root, relative);
  const fromRoot = path.relative(root, absolute);
  if (path.isAbsolute(relative) || fromRoot.startsWith('..' + path.sep) || fromRoot === '..' || path.isAbsolute(fromRoot)) {
    throw new Error(`Path escapes project/output: ${relative}`);
  }
  return absolute;
}
function write(name, payload) {
  const target = inside(output, name);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(target, payload);
}

const descriptor = read('Project.heproject');
const scenePath = read(descriptor.GameConfig).Game.DefaultScene;
const scene = read(scenePath);
const contract = read('Config/SharedContent.json');
const data = read('Config/GameplayCatalog.json');
data.sharedUi = read('Config/SharedUI.json').documents;
data.scenePath = scenePath;
const portableFallbacks = {};
for (const entity of Object.values(scene)) {
  for (const key of Object.keys(entity)) {
    if (Object.hasOwn(contract.portableComponentFallbacks, key)) portableFallbacks[key] = contract.portableComponentFallbacks[key];
  }
}
const sharedContent = {scenePath, gameConfig: descriptor.GameConfig, portableFallbacks};
if (catalogOnly) {
  const dependencies = new Set(Object.values(data.nativeWeaponVfx).flatMap(v => Object.values(v)).filter(Boolean));
  Object.values(data.nativeCommonVfx).forEach(v => dependencies.add(v));
  write('SurvivorNativeDependencies.cs', '// Generated from Config/GameplayCatalog.json. Do not edit.\nnamespace GameScripts;\n' +
    [...dependencies].sort().map(v => `[HEngine.ScriptDependency(${JSON.stringify(v)})]`).join('\n') +
    '\npublic sealed partial class SurvivorNativeGame {}\n');
}
write('catalog.json', JSON.stringify(data));
write('rendering.json', JSON.stringify(read('Config/PortableRendering.json')));
if (catalogOnly) process.exit(0);

const extensions = new Set(['.hmesh','.hmat','.bin','.png','.jpg','.jpeg','.hanim','.hanimctrl','.hskel','.he','.hprefab','.wav','.ogg','.mp3','.hui','.rml','.rcss','.ttf','.otf']);
const jsonExtensions = new Set(['.hmesh','.hmat','.hanim','.hanimctrl','.hskel','.he','.hprefab','.hui']);
const pending = new Set([scenePath,'Assets/UI/Backgrounds/starbloom_title_bg.png','Assets/UI/Backgrounds/starbloom_loading_bg.png']);
const copied = {};
function collect(value) {
  if (typeof value === 'string') {
    const name = value.replaceAll('\\', '/');
    if (name.startsWith('Assets/') && extensions.has(path.extname(name).toLowerCase())) pending.add(name);
  } else if (value && typeof value === 'object') {
    Object.values(value).forEach(collect);
  }
}
function copy(source, name) {
  const payload = fs.readFileSync(source);
  write(name, payload);
  copied[name] = {bytes: payload.length, sha256: crypto.createHash('sha256').update(payload).digest('hex')};
  return payload;
}
collect(data);
while (pending.size) {
  const name = [...pending].sort()[0]; pending.delete(name);
  if (Object.hasOwn(copied, name)) continue;
  const payload = copy(inside(project, name), name);
  if (jsonExtensions.has(path.extname(name).toLowerCase())) collect(JSON.parse(payload.toString('utf8')));
}
const web = path.join(project, 'Web');
for (const entry of fs.readdirSync(web, {withFileTypes: true})) {
  if (entry.isFile()) write(entry.name, fs.readFileSync(path.join(web, entry.name)));
}
for (const license of read('Config/Package.json').Licenses) {
  copy(inside(project, license.Source), 'Licenses/' + license.Output);
}
write('content-manifest.json', JSON.stringify({schema: 1, game: '小树保卫者', gameplay: 'C#', sharedContent, assets: copied}, null, 2));
console.log(`Exported ${Object.keys(copied).length} assets: ${output}`);
