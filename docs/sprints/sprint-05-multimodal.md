# Sprint 5 — Multi-Modal Support (Images from Documents)

## Goal

Add **image extraction** and **captioning** from educational documents, enabling the system to retrieve and display relevant diagrams, charts, and formulas alongside text explanations. Critical for ML/Math courses where visual content is essential.

**Post-MVP Focus:** Enhance learning experience with visual aids — especially important for technical subjects.

## Link to description

- **Implementation Plan:** [Phase 4: Multi-Modal](../description.md#phase-4-multi-modal)
- **Modules:** [Module 4: Multi-Modal Features](../description.md#module-4-multi-modal-features)
- **Stack:** PyMuPDF for extraction, GPT-4o Vision or LLaVA for captioning, MinIO or local storage

## Scope (in)

### 1. Image Extraction (2-3 days)

**Extract images from PDFs:**
- Use `PyMuPDF` (fitz) to extract images from PDF pages
- Link images to text chunks by page number and position
- Store image metadata: page, position, size, format

**Extract images from DOCX:**
- Use `python-docx` to extract embedded images
- Link to surrounding text paragraphs

**Storage:**
- Local filesystem for MVP (e.g., `data/images/{document_id}/{image_id}.png`)
- Or MinIO (S3-compatible) if you want production-like setup
- Store image paths in PostgreSQL

### 2. Image Captioning (2-3 days)

**Generate descriptions with VLM:**
- Use GPT-4o Vision API: send image + prompt "Describe this educational diagram/chart"
- Or use open-source LLaVA (requires GPU, more complex)
- Generate detailed captions focusing on educational content

**Caption prompt template:**
```
You are analyzing an image from an educational document.
Describe what you see in detail, focusing on:
- Type of visual (diagram, chart, formula, screenshot, etc.)
- Key concepts illustrated
- Labels, axes, annotations
- Educational purpose

Image context: [surrounding text from document]
```

**Store captions:**
- Save caption text in PostgreSQL linked to image
- Optionally embed captions for semantic search

### 3. Image Indexing & Retrieval (2-3 days)

**Index captions in Qdrant:**
- Embed image captions using same embedding model as text
- Store in Qdrant with metadata: image_path, page, document_id
- Enable semantic search over images

**Hybrid retrieval:**
- Retrieve both text chunks and relevant images
- Rank by relevance score
- Return top-3 text chunks + top-2 images

**Image-text binding:**
- When retrieving text chunk, check if nearby images exist (same page ± 1)
- Include related images in response even if not directly retrieved

### 4. Display Images in Responses (1-2 days)

**API changes:**
- Extend response schema to include `images` field:
```json
{
  "answer": "Recursion works by...",
  "citations": [...],
  "images": [
    {
      "url": "/api/v1/images/{image_id}",
      "caption": "Diagram showing recursive call stack",
      "source": "chapter3.pdf",
      "page": 42
    }
  ]
}
```

**Image serving endpoint:**
- `GET /api/v1/images/{image_id}` — serve image file
- Add proper CORS headers for Streamlit

**Streamlit UI:**
- Display images inline in chat responses
- Show caption and source below image
- Expandable/collapsible image sections

### 5. Image Quality & Filtering (1 day)

**Filter out low-quality images:**
- Skip images smaller than 100x100 pixels
- Skip decorative images (logos, icons) — use heuristics or VLM classification
- Focus on educational content: diagrams, charts, formulas, screenshots

**Image preprocessing:**
- Convert to standard format (PNG or JPEG)
- Resize large images for faster loading
- Optimize for web display

## Out of scope

- CLIP embeddings for direct image-text matching (caption-based search is simpler)
- Image generation or editing
- OCR for text in images (VLM captions are sufficient)
- Video/animation support
- Advanced image analysis (object detection, segmentation)

## Technical pointers

- **PyMuPDF:** `doc.get_page_images()` returns image metadata; `doc.extract_image()` gets bytes
- **GPT-4o Vision:** Cost is ~$0.01 per image; batch process during upload to save time
- **Storage:** Local filesystem is fine for MVP; MinIO adds complexity
- **Captioning quality:** Test prompts to get useful educational descriptions

## Readiness criteria

- [ ] Images are extracted from PDF and DOCX documents
- [ ] Captions are generated for at least 10 test images (manually verify quality)
- [ ] Image captions are indexed in Qdrant and retrievable
- [ ] API returns images with text responses for relevant queries
- [ ] Streamlit UI displays images inline with captions and sources
- [ ] Low-quality/decorative images are filtered out
- [ ] Image serving endpoint works (`GET /api/v1/images/{id}`)

## Example interaction

**Query:** "How does a neural network forward pass work?"

**Response:**
```
Text: "A neural network forward pass involves..."
Citations: [1] Deep Learning Basics, Page 23

Images:
[Image: Neural network architecture diagram]
Caption: "Diagram showing input layer, hidden layers, and output layer 
         with forward propagation arrows"
Source: deep_learning.pdf, Page 23
```

## Risks and dependencies

- **VLM cost:** GPT-4o Vision is expensive; budget accordingly or use open-source LLaVA
- **Caption quality:** VLM may generate generic descriptions; prompt engineering is critical
- **Storage:** Images can be large; consider storage limits
- **Latency:** Image captioning during upload adds processing time

## Estimated effort

**1-1.5 weeks** (7-10 days):
- Days 1-3: Image extraction from PDF/DOCX
- Days 4-6: Captioning with VLM
- Days 7-8: Indexing and retrieval
- Days 9-10: API changes and UI integration

---

**Sprint label (GitHub):** `sprint:5`
