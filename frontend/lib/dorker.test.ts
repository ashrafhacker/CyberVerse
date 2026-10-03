import { describe, expect, it } from 'vitest';
import { buildDork, buildSearchUrl, DORK_ENGINES, DORK_PRESETS } from './dorker';

describe('DORK_PRESETS', () => {
  it('covers all six categories', () => {
    expect(DORK_PRESETS.map((preset) => preset.id)).toEqual([
      'video',
      'book',
      'music',
      'archive',
      'picture',
      'all',
    ]);
  });

  it('keeps the original extension lists', () => {
    const video = DORK_PRESETS.find((preset) => preset.id === 'video');
    expect(video?.extensions).toBe('mkv|mp4|avi|mov|mpg|wmv|divx|mpeg');
    const books = DORK_PRESETS.find((preset) => preset.id === 'book');
    expect(books?.extensions).toContain('EPUB');
  });

  it('supports five engines', () => {
    expect(DORK_ENGINES.map((engine) => engine.id)).toEqual([
      'google',
      'googol',
      'startpage',
      'searx',
      'filepursuit',
    ]);
  });
});

describe('buildDork', () => {
  it('returns empty string for blank queries', () => {
    expect(buildDork('   ', 'video')).toBe('');
  });

  it('appends extensions for a selected filetype', () => {
    const dork = buildDork('The.Blacklist', 'video');
    expect(dork).toBe(
      'The.Blacklist +(mkv|mp4|avi|mov|mpg|wmv|divx|mpeg) ' +
        '-inurl:(jsp|pl|php|html|aspx|htm|cf|shtml) intitle:index.of ' +
        '-inurl:(listen77|mp3raid|mp3toss|mp3drug|index_of|index-of|wallywashis|downloadmana)',
    );
  });

  it('omits the extension block for "other"', () => {
    const dork = buildDork('something', 'all');
    expect(dork).not.toContain('+(');
    expect(dork).toContain('intitle:index.of');
  });
});

describe('buildSearchUrl', () => {
  it('builds a google url with the encoded dork', () => {
    const url = buildSearchUrl('foo bar', 'video', 'google');
    const decoded = decodeURIComponent(url);
    expect(url.startsWith('https://www.google.com/search?q=')).toBe(true);
    expect(decoded).toContain('foo bar +(mkv|mp4|avi|mov|mpg|wmv|divx|mpeg)');
    expect(decoded).toContain('intitle:index.of');
  });

  it('uses the resType path for filepursuit', () => {
    const url = buildSearchUrl('foo bar', 'book', 'filepursuit');
    expect(url).toBe('https://filepursuit.com/search/foo+bar/type/ebook');
  });

  it('defaults filepursuit type to all for "other"', () => {
    const url = buildSearchUrl('anything', 'all', 'filepursuit');
    expect(url).toBe('https://filepursuit.com/search/anything/type/all');
  });

  it('returns empty string for blank queries', () => {
    expect(buildSearchUrl('', 'video', 'google')).toBe('');
  });
});
