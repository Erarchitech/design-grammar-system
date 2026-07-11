// DG API Docs content aggregator.
// Each ##-*.js file in this directory exports a section object
// {id, title, pages: [...]}. Adding a file = adding a section,
// no viewer changes needed.

const modules = import.meta.glob("./##-*.js", { eager: true });

const entries = Object.entries(modules)
  .filter(([_, mod]) => mod && mod.default && mod.default.id)
  .map(([path, mod]) => ({ path, ...mod.default }));

// Sort by filename prefix (##-) so sections appear in order
entries.sort((a, b) => {
  const aNum = parseInt(a.path.match(/(\d+)/)?.[1] || "99", 10);
  const bNum = parseInt(b.path.match(/(\d+)/)?.[1] || "99", 10);
  return aNum - bNum;
});

export default entries;
