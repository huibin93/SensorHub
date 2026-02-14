/* eslint-disable no-undef */
import { init, compress, decompress } from '@bokuweb/zstd-wasm';
import SparkMD5 from 'spark-md5';

// 使用分片读取计算大文件 Hash,防止爆内存
async function calculateHash(file) {
  return new Promise((resolve, reject) => {
    const chunkSize = 20 * 1024 * 1024; // 20MB一片
    const chunks = Math.ceil(file.size / chunkSize);
    const spark = new SparkMD5.ArrayBuffer();
    const fileReader = new FileReader();
    let currentChunk = 0;

    fileReader.onload = (e) => {
      spark.append(e.target.result);
      currentChunk++;
      if (currentChunk < chunks) {
        loadNext();
      } else {
        resolve(spark.end()); // 返回 Hex Hash
      }
    };

    fileReader.onerror = () => reject('Read error');

    function loadNext() {
      const start = currentChunk * chunkSize;
      const end = start + chunkSize >= file.size ? file.size : start + chunkSize;
      fileReader.readAsArrayBuffer(file.slice(start, end));
    }

    loadNext();
  });
}

self.onmessage = async (e) => {
  const { id, action, file, level } = e.data;

  try {
    let result = {};

    if (action === 'calcHash') {
      // === 动作1：只计算 Hash (用于秒传检查) ===
      const hash = await calculateHash(file);
      result = { status: 'hash_done', hash };

    } else if (action === 'hashAndCompress') {
      // === 动作2：单次扫描完成 Hash + 压缩（换行对齐分帧） ===
      if (!self.zstdInitialized) {
        await init('/zstd.wasm');
        self.zstdInitialized = true;
      }

      const sourceArrayBuffer = await file.arrayBuffer();
      const buffer = new Uint8Array(sourceArrayBuffer);

      const spark = new SparkMD5.ArrayBuffer();
      spark.append(sourceArrayBuffer);
      const hash = spark.end();

      const compressedChunks = [];
      const frameIndex = [];
      let compressedOffset = 0;

      const MIN_CHUNK_SIZE = 2 * 1024 * 1024; // 2MB minimum
      const MAX_CHUNK_SIZE = 4 * 1024 * 1024; // 4MB maximum
      const NEWLINE = 0x0A; // \n

      let offset = 0;
      let frameIdx = 0;

      while (offset < buffer.length) {
        try {
          let end = Math.min(offset + MIN_CHUNK_SIZE, buffer.length);
          let endsWithNewline = false;

          if (end < buffer.length) {
            const maxEnd = Math.min(offset + MAX_CHUNK_SIZE, buffer.length);

            while (end < maxEnd && buffer[end] !== NEWLINE) {
              end++;
            }

            if (end < buffer.length && buffer[end] === NEWLINE) {
              end++;
              endsWithNewline = true;
            }
          }

          if (!endsWithNewline && end > 0 && buffer[end - 1] === NEWLINE) {
            endsWithNewline = true;
          }

          const chunk = buffer.slice(offset, end);
          const compressedChunk = compress(chunk, level || 6);
          compressedChunks.push(compressedChunk);

          frameIndex.push({
            cs: compressedOffset,
            cl: compressedChunk.length,
            ds: offset,
            dl: chunk.length,
            nl: endsWithNewline
          });

          compressedOffset += compressedChunk.length;
          offset = end;
          frameIdx++;
        } catch (chunkErr) {
          throw new Error(`Compression failed at frame ${frameIdx}: ${chunkErr.message}`);
        }
      }

      const blob = new Blob(compressedChunks, { type: 'application/zstd' });
      result = {
        status: 'hash_compress_done',
        hash,
        blob,
        frameIndex: {
          version: 2,
          frameSize: MIN_CHUNK_SIZE,
          maxFrameSize: MAX_CHUNK_SIZE,
          lineAligned: true,
          originalSize: file.size,
          compressedSize: blob.size,
          frames: frameIndex
        }
      };

    } else if (action === 'compress') {
      // === 动作2：执行压缩 (换行对齐分帧) ===
      if (!self.zstdInitialized) {
        await init('/zstd.wasm');
        self.zstdInitialized = true;
      }

      const compressedChunks = [];
      const frameIndex = [];
      let compressedOffset = 0;

      const MIN_CHUNK_SIZE = 2 * 1024 * 1024; // 2MB minimum
      const MAX_CHUNK_SIZE = 4 * 1024 * 1024; // 4MB maximum
      const NEWLINE = 0x0A; // \n

      // 读取整个文件到 buffer
      const buffer = new Uint8Array(await file.arrayBuffer());
      let offset = 0;
      let frameIdx = 0;

      while (offset < buffer.length) {
        try {
          // 计算初始结束位置 (至少 2MB)
          let end = Math.min(offset + MIN_CHUNK_SIZE, buffer.length);
          let endsWithNewline = false;

          // 如果不是文件末尾, 向后搜索换行符
          if (end < buffer.length) {
            const maxEnd = Math.min(offset + MAX_CHUNK_SIZE, buffer.length);

            // 从 end 向后搜索 \n (最多到 maxEnd)
            while (end < maxEnd && buffer[end] !== NEWLINE) {
              end++;
            }

            if (end < buffer.length && buffer[end] === NEWLINE) {
              end++; // 包含换行符
              endsWithNewline = true;
            }
            // 如果在 maxEnd 内未找到换行, 就在 maxEnd 处切割
          }

          // 检查最后一个字符是否为换行
          if (!endsWithNewline && end > 0 && buffer[end - 1] === NEWLINE) {
            endsWithNewline = true;
          }

          // 提取并压缩
          const chunk = buffer.slice(offset, end);
          const compressedChunk = compress(chunk, level || 6);
          compressedChunks.push(compressedChunk);

          // 记录帧索引
          frameIndex.push({
            cs: compressedOffset,
            cl: compressedChunk.length,
            ds: offset,
            dl: chunk.length,
            nl: endsWithNewline  // 是否以换行结束
          });

          compressedOffset += compressedChunk.length;
          offset = end;
          frameIdx++;
        } catch (chunkErr) {
          throw new Error(`Compression failed at frame ${frameIdx}: ${chunkErr.message}`);
        }
      }

      const blob = new Blob(compressedChunks, { type: 'application/zstd' });
      result = {
        status: 'compress_done',
        blob,
        frameIndex: {
          version: 2,  // 版本号升级
          frameSize: MIN_CHUNK_SIZE,
          maxFrameSize: MAX_CHUNK_SIZE,
          lineAligned: true,
          originalSize: file.size,
          compressedSize: blob.size,
          frames: frameIndex
        }
      };

    } else if (action === 'decompress') {
      // === 动作3：执行解压 ===
      if (!self.zstdInitialized) {
        await init('/zstd.wasm');
        self.zstdInitialized = true;
      }

      const arrayBuffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);

      // Decompress
      const decompressed = decompress(uint8Array);
      const blob = new Blob([decompressed], { type: 'application/octet-stream' });
      result = { status: 'decompress_done', blob };
    }

    // 带上 ID 返回
    self.postMessage({ id, ...result });

  } catch (err) {
    self.postMessage({ id, status: 'error', message: err.message });
  }
};
