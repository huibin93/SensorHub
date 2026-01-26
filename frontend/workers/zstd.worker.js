/* eslint-disable no-undef */
import { init, compress } from '@bokuweb/zstd-wasm';
import SparkMD5 from 'spark-md5';

// 使用分片读取计算大文件 Hash，防止爆内存
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
      await init('/zstd.wasm');
      const arrayBuffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      const compressedArray = compress(uint8Array, level || 3);
      const blob = new Blob([compressedArray], { type: 'application/zstd' });

      result = { status: 'compress_done', blob };
    }

    // 带上 ID 返回
    self.postMessage({ id, ...result });

  } catch (err) {
    self.postMessage({ id, status: 'error', message: err.message });
  }
};
