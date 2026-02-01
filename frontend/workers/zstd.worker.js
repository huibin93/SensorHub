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

    } else if (action === 'compress') {
      // === 动作2：执行压缩 ===
      // Load zstd.wasm from public folder
      if (!self.zstdInitialized) {
        await init('/zstd.wasm');
        self.zstdInitialized = true;
      }

      const compressedChunks = [];
      const frameIndex = [];  // 帧索引表
      let compressedOffset = 0;   // 压缩数据累计偏移
      let decompressedOffset = 0; // 原始数据累计偏移
      const chunkSize = 2 * 1024 * 1024; // 2MB chunks
      const totalChunks = Math.ceil(file.size / chunkSize);

      for (let i = 0; i < totalChunks; i++) {
        try {
          const start = i * chunkSize;
          const end = Math.min(start + chunkSize, file.size);
          const chunkBlob = file.slice(start, end);
          const arrayBuffer = await chunkBlob.arrayBuffer();
          const uint8Array = new Uint8Array(arrayBuffer);

          // Compress chunk (Creates a self-contained Zstd frame)
          const compressedChunk = compress(uint8Array, level || 6);
          compressedChunks.push(compressedChunk);

          // Record frame info for index
          frameIndex.push({
            cs: compressedOffset,       // compressed_start
            cl: compressedChunk.length, // compressed_length
            ds: decompressedOffset,     // decompressed_start
            dl: uint8Array.length       // decompressed_length
          });

          compressedOffset += compressedChunk.length;
          decompressedOffset += uint8Array.length;
        } catch (chunkErr) {
          throw new Error(`Compression failed at chunk ${i}: ${chunkErr.message}`);
        }
      }

      const blob = new Blob(compressedChunks, { type: 'application/zstd' });
      result = {
        status: 'compress_done',
        blob,
        frameIndex: {
          version: 1,
          frameSize: chunkSize,
          originalSize: file.size,      // 原始文件大小
          compressedSize: blob.size,    // 压缩后大小
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
