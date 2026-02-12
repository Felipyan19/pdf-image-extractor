#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = {
    input: null,
    outputTemplate: null,
    outputJson: null,
  };

  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--input') args.input = argv[++i];
    else if (arg === '--output-template') args.outputTemplate = argv[++i];
    else if (arg === '--output-json') args.outputJson = argv[++i];
  }

  if (!args.input || !args.outputTemplate || !args.outputJson) {
    throw new Error(
      'Usage: node extract_template_content.js --input <template.html> --output-template <template.dynamic.html> --output-json <template.content.json>'
    );
  }

  return args;
}

function isLikelyImageUrl(value) {
  if (!value) return false;
  const url = String(value).trim();
  if (!url) return false;
  if (/^data:image\//i.test(url)) return true;
  return /\.(png|jpe?g|gif|webp|svg|bmp|avif)([?#].*)?$/i.test(url);
}

function makeCounter(prefix) {
  let i = 1;
  return () => `${prefix}_${String(i++).padStart(4, '0')}`;
}

function replaceImageUrls(html, data, images) {
  const nextImageKey = makeCounter('image');
  const imageMap = new Map();

  const getOrCreateImageKey = (value) => {
    if (imageMap.has(value)) return imageMap.get(value);
    const key = nextImageKey();
    imageMap.set(value, key);
    images[key] = value;
    data[key] = value;
    return key;
  };

  // src="...", background="..."
  let out = html.replace(
    /\b(src|background)\s*=\s*("([^"]*)"|'([^']*)')/gi,
    (full, attr, quoted, doubleValue, singleValue) => {
      const value = doubleValue ?? singleValue ?? '';
      if (!isLikelyImageUrl(value)) return full;
      const quote = quoted[0];
      const key = getOrCreateImageKey(value);
      return `${attr}=${quote}{{${key}}}${quote}`;
    }
  );

  // url('...') in inline CSS / style blocks.
  out = out.replace(/url\(\s*(['"]?)([^'")]+)\1\s*\)/gi, (full, quote, value) => {
    if (!isLikelyImageUrl(value)) return full;
    const key = getOrCreateImageKey(value);
    const token = `{{${key}}}`;
    if (quote) return `url(${quote}${token}${quote})`;
    return `url(${token})`;
  });

  return out;
}

function tokenizeTextNodes(html, data, texts) {
  const nextTextKey = makeCounter('text');
  let out = '';
  let i = 0;
  let inStyle = false;
  let inScript = false;

  while (i < html.length) {
    const ch = html[i];

    if (ch === '<') {
      // HTML comments
      if (html.startsWith('<!--', i)) {
        const endComment = html.indexOf('-->', i + 4);
        if (endComment === -1) {
          out += html.slice(i);
          break;
        }
        out += html.slice(i, endComment + 3);
        i = endComment + 3;
        continue;
      }

      const endTag = html.indexOf('>', i + 1);
      if (endTag === -1) {
        out += html.slice(i);
        break;
      }

      const tagChunk = html.slice(i, endTag + 1);
      out += tagChunk;

      const tagMatch = /^<\s*(\/?)\s*([a-zA-Z0-9:-]+)/.exec(tagChunk);
      if (tagMatch) {
        const isClosing = tagMatch[1] === '/';
        const tagName = tagMatch[2].toLowerCase();
        if (tagName === 'style') inStyle = !isClosing;
        if (tagName === 'script') inScript = !isClosing;
      }

      i = endTag + 1;
      continue;
    }

    const nextTag = html.indexOf('<', i);
    const end = nextTag === -1 ? html.length : nextTag;
    const textChunk = html.slice(i, end);

    const shouldTokenize =
      !inStyle &&
      !inScript &&
      textChunk.trim().length > 0 &&
      !textChunk.includes('{{') &&
      !textChunk.includes('}}');

    if (shouldTokenize) {
      const key = nextTextKey();
      texts[key] = textChunk;
      data[key] = textChunk;
      out += `{{${key}}}`;
    } else {
      out += textChunk;
    }

    i = end;
  }

  return out;
}

function main() {
  const args = parseArgs(process.argv);
  const inputPath = path.resolve(args.input);
  const outTemplatePath = path.resolve(args.outputTemplate);
  const outJsonPath = path.resolve(args.outputJson);

  const rawHtml = fs.readFileSync(inputPath, 'utf8');
  const data = {};
  const texts = {};
  const images = {};

  const imageTokenized = replaceImageUrls(rawHtml, data, images);
  const tokenizedTemplate = tokenizeTextNodes(imageTokenized, data, texts);

  const payload = {
    meta: {
      source_template: path.basename(inputPath),
      generated_at: new Date().toISOString(),
      counts: {
        texts: Object.keys(texts).length,
        images: Object.keys(images).length,
        total_slots: Object.keys(data).length,
      },
    },
    data,
    texts,
    images,
  };

  fs.writeFileSync(outTemplatePath, tokenizedTemplate, 'utf8');
  fs.writeFileSync(outJsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');

  process.stdout.write(
    `Generated template: ${outTemplatePath}\nGenerated JSON: ${outJsonPath}\nSlots: ${payload.meta.counts.total_slots} (texts=${payload.meta.counts.texts}, images=${payload.meta.counts.images})\n`
  );
}

main();
