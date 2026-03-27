const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');
const mammoth = require('mammoth');
const xlsx = require('node-xlsx');
const sharp = require('sharp');
const ffmpeg = require('fluent-ffmpeg');

class DocumentProcessor {
  constructor() {
    this.supportedTypes = {
      'application/pdf': 'processPDF',
      'application/msword': 'processDoc',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'processDocx',
      'text/plain': 'processText',
      'text/rtf': 'processText',
      'application/vnd.ms-excel': 'processExcel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'processExcel',
      'application/vnd.ms-powerpoint': 'processPowerPoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'processPowerPoint',
      'image/jpeg': 'processImage',
      'image/png': 'processImage',
      'image/gif': 'processImage'
    };
  }

  async processDocument(filePath, mimeType, metadata = {}) {
    try {
      const processor = this.supportedTypes[mimeType];
      if (!processor) {
        throw new Error(`Unsupported file type: ${mimeType}`);
      }

      const result = await this[processor](filePath, metadata);
      
      return {
        success: true,
        text: result.text,
        metadata: result.metadata || {},
        thumbnails: result.thumbnails || [],
        pageCount: result.pageCount || 1,
        wordCount: this.countWords(result.text),
        processingTime: result.processingTime
      };
    } catch (error) {
      console.error('Document processing error:', error);
      return {
        success: false,
        error: error.message,
        text: '',
        metadata: {},
        thumbnails: [],
        pageCount: 0,
        wordCount: 0
      };
    }
  }

  async processPDF(filePath, metadata) {
    const startTime = Date.now();
    const dataBuffer = fs.readFileSync(filePath);
    const data = await pdf(dataBuffer);
    
    const thumbnails = [];
    if (data.numpages > 0) {
      const thumbnailDir = path.join(path.dirname(filePath), 'thumbnails');
      if (!fs.existsSync(thumbnailDir)) {
        fs.mkdirSync(thumbnailDir, { recursive: true });
      }

      for (let i = 1; i <= Math.min(data.numpages, 5); i++) {
        try {
          const thumbnailPath = path.join(thumbnailDir, `page_${i}.png`);
          await this.generatePDFThumbnail(filePath, thumbnailPath, i);
          thumbnails.push({
            page: i,
            path: thumbnailPath,
            width: 200,
            height: 280
          });
        } catch (error) {
          console.error(`Error generating thumbnail for page ${i}:`, error);
        }
      }
    }

    return {
      text: data.text,
      metadata: {
        ...metadata,
        pageCount: data.numpages,
        info: data.info || {}
      },
      thumbnails,
      pageCount: data.numpages,
      processingTime: Date.now() - startTime
    };
  }

  async processDocx(filePath, metadata) {
    const startTime = Date.now();
    const result = await mammoth.extractRawText({ path: filePath });
    
    return {
      text: result.value,
      metadata,
      thumbnails: [],
      pageCount: 1,
      processingTime: Date.now() - startTime
    };
  }

  async processText(filePath, metadata) {
    const startTime = Date.now();
    const text = fs.readFileSync(filePath, 'utf8');
    
    return {
      text,
      metadata,
      thumbnails: [],
      pageCount: 1,
      processingTime: Date.now() - startTime
    };
  }

  async processExcel(filePath, metadata) {
    const startTime = Date.now();
    const workSheets = xlsx.parse(fs.readFileSync(filePath));
    let text = '';
    
    workSheets.forEach((sheet, index) => {
      text += `Sheet ${index + 1}: ${sheet.name}\n`;
      sheet.data.forEach(row => {
        text += row.join('\t') + '\n';
      });
      text += '\n';
    });

    return {
      text,
      metadata: {
        ...metadata,
        sheetCount: workSheets.length
      },
      thumbnails: [],
      pageCount: 1,
      processingTime: Date.now() - startTime
    };
  }

  async processImage(filePath, metadata) {
    const startTime = Date.now();
    const metadata_image = await sharp(filePath).metadata();
    
    const thumbnailDir = path.join(path.dirname(filePath), 'thumbnails');
    if (!fs.existsSync(thumbnailDir)) {
      fs.mkdirSync(thumbnailDir, { recursive: true });
    }

    const thumbnailPath = path.join(thumbnailDir, `thumbnail_${path.basename(filePath)}`);
    await sharp(filePath)
      .resize(200, 200, { fit: 'inside' })
      .png()
      .toFile(thumbnailPath);

    return {
      text: metadata.text || '',
      metadata: {
        ...metadata,
        width: metadata_image.width,
        height: metadata_image.height,
        format: metadata_image.format
      },
      thumbnails: [{
        page: 1,
        path: thumbnailPath,
        width: metadata_image.width,
        height: metadata_image.height
      }],
      pageCount: 1,
      processingTime: Date.now() - startTime
    };
  }

  async processPowerPoint(filePath, metadata) {
    const startTime = Date.now();
    return {
      text: '',
      metadata: {
        ...metadata,
        note: 'PowerPoint processing requires additional libraries'
      },
      thumbnails: [],
      pageCount: 1,
      processingTime: Date.now() - startTime
    };
  }

  countWords(text) {
    if (!text) return 0;
    return text.trim().split(/\s+/).filter(word => word.length > 0).length;
  }

  async generatePDFThumbnail(pdfPath, outputPath, pageNumber) {
    return new Promise((resolve, reject) => {
      ffmpeg(pdfPath)
        .screenshots({
          count: 1,
          folder: path.dirname(outputPath),
          filename: path.basename(outputPath),
          timemarks: [pageNumber * 1000]
        })
        .on('end', resolve)
        .on('error', reject);
    });
  }

  async extractAudioTranscription(filePath) {
    return {
      text: 'Audio transcription requires external service integration',
      metadata: {
        note: 'Integrate with speech-to-text service'
      }
    };
  }

  async extractVideoTranscription(filePath) {
    return {
      text: 'Video transcription requires external service integration',
      metadata: {
        note: 'Integrate with speech-to-text and video analysis services'
      }
    };
  }

  async generateDocumentSummary(text, maxLength = 200) {
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [];
    if (sentences.length <= 3) {
      return text.substring(0, maxLength) + (text.length > maxLength ? '...' : '');
    }
    
    return sentences.slice(0, 3).join(' ').substring(0, maxLength) + '...';
  }

  async extractKeywords(text, maxKeywords = 10) {
    const words = text.toLowerCase().match(/\b\w+\b/g) || [];
    const wordFreq = {};
    
    words.forEach(word => {
      if (word.length > 3) {
        wordFreq[word] = (wordFreq[word] || 0) + 1;
      }
    });

    return Object.entries(wordFreq)
      .sort((a, b) => b[1] - a[1])
      .slice(0, maxKeywords)
      .map(([word]) => word);
  }
}

module.exports = DocumentProcessor;