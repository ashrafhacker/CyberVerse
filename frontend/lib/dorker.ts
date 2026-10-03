export type DorkCategory = 'video' | 'book' | 'music' | 'archive' | 'picture' | 'all';

export type DorkEngine = 'google' | 'googol' | 'startpage' | 'searx' | 'filepursuit';

export interface DorkPreset {
  id: DorkCategory;
  label: string;
  extensions: string | null;
  resType: string;
  placeholder: string;
}

export const DORK_PRESETS: DorkPreset[] = [
  {
    id: 'video',
    label: 'TV/Movies/Video',
    extensions: 'mkv|mp4|avi|mov|mpg|wmv|divx|mpeg',
    resType: 'video',
    placeholder: 'eg. The.Blacklist.S01',
  },
  {
    id: 'book',
    label: 'Books',
    extensions: 'MOBI|CBZ|CBR|CBC|CHM|EPUB|FB2|LIT|LRF|ODT|PDF|PRC|PDB|PML|RB|RTF|TCR|DOC|DOCX',
    resType: 'ebook',
    placeholder: 'eg. 1984',
  },
  {
    id: 'music',
    label: 'Music',
    extensions: 'mp3|wav|ac3|ogg|flac|wma|m4a|aac|mod',
    resType: 'audio',
    placeholder: 'eg. K.Flay discography',
  },
  {
    id: 'archive',
    label: 'Software/ISO/DMG/Games',
    extensions: 'exe|iso|dmg|tar|7z|bz2|gz|rar|zip|apk',
    resType: 'archive',
    placeholder: 'eg. GTA V',
  },
  {
    id: 'picture',
    label: 'Images',
    extensions: 'jpg|png|bmp|gif|tif|tiff|psd',
    resType: 'picture',
    placeholder: 'eg. city skyline',
  },
  {
    id: 'all',
    label: 'Other',
    extensions: null,
    resType: 'all',
    placeholder: 'Search anything',
  },
];

export const DORK_ENGINES: { id: DorkEngine; label: string }[] = [
  { id: 'google', label: 'Google' },
  { id: 'googol', label: 'Googol' },
  { id: 'startpage', label: 'Startpage' },
  { id: 'searx', label: 'Searx' },
  { id: 'filepursuit', label: 'FilePursuit' },
];

const INDEX_OF_FILTER =
  '-inurl:(jsp|pl|php|html|aspx|htm|cf|shtml) intitle:index.of ' +
  '-inurl:(listen77|mp3raid|mp3toss|mp3drug|index_of|index-of|wallywashis|downloadmana)';

export function buildDork(query: string, category: DorkCategory): string {
  const trimmed = query.trim();
  if (!trimmed) return '';
  const extensions = DORK_PRESETS.find((preset) => preset.id === category)?.extensions;
  return extensions
    ? `${trimmed} +(${extensions}) ${INDEX_OF_FILTER}`
    : `${trimmed} ${INDEX_OF_FILTER}`;
}

export function buildSearchUrl(query: string, category: DorkCategory, engine: DorkEngine): string {
  const trimmed = query.trim();
  if (!trimmed) return '';
  const preset = DORK_PRESETS.find((candidate) => candidate.id === category);
  if (engine === 'filepursuit') {
    return `https://filepursuit.com/search/${trimmed.replace(/ /g, '+')}/type/${preset?.resType ?? 'all'}`;
  }
  const dork = buildDork(trimmed, category);
  const endpoint = {
    google: 'https://www.google.com/search?q=',
    googol: 'https://googol.warriordudimanche.net/?q=',
    startpage: 'https://www.startpage.com/do/dsearch?query=',
    searx: 'https://searx.me/?q=',
  }[engine];
  return `${endpoint}${encodeURIComponent(dork)}`;
}
