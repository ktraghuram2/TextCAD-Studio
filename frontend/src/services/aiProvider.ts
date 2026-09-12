import { ModelSpecification, GeometricFeature, parseFeaturesFromCode } from './cadCompiler';

export const CAD_SYSTEM_INSTRUCTION = `You are a world-class mechanical CAD engineer and Python CAD programmer specializing in CadQuery and Build123d.
Your goal is to translate natural language design prompts into:
1. Production-grade, mathematically accurate, and comprehensive Python CAD code (using Build123d or CadQuery).
2. A structured geometric feature breakdown representing ALL components of the design for instant rendering.

CRITICAL CODE QUALITY RULES:
- NEVER generate trivial, minimalist 2-line placeholder scripts.
- Write complete, robust, production-grade Python code (typically 15 to 50 lines) that fully implements all geometric features, clearances, fillets, chamfers, mounting patterns, cavities, and polar locations described in the prompt.
- Use explicit numeric dimensions in millimeters (mm).

2D SKETCH vs 3D SOLID RULES:
- When the prompt requests a 2D drawing, 2D sketch, planar shape, or profile (e.g. "draw a rectangle", "circle", "2d flower", "sketch of...", "drawing with rectangle and circle", "polygon", "slot", without 3D depth/height/extrusion):
  1. Generate Build123d BuildSketch() Python code. Example for a 2D flower / polar array:
     from build123d import *

     with BuildSketch() as sketch:
         # Central hub / disc
         Circle(radius=15)
         # Petals / peripheral features arranged in polar array
         with Locations(PolarLocations(radius=20, count=6)):
             Circle(radius=12)

     if 'show_object' in globals():
         show_object(sketch)
  2. Set "is2D": true
  3. Set "dimensions": { "width": width, "height": height, "depth": 0 }
  4. In "features", list ALL shapes (including each polar component with its calculated [x, y, 0] position).

- When the prompt requests a 3D solid part, bracket, mount, enclosure, flange, mechanical assembly, or specifies 3D dimensions (height, depth, thickness, extrusion):
  1. Generate Build123d BuildPart() Python code. Example for a heavy-duty L-bracket / stepper motor mount:
     from build123d import *

     with BuildPart() as mount:
         # Vertical motor mounting faceplate (42x50x5 mm)
         Box(42, 50, 5)
         # Horizontal base mounting plate (42x40x5 mm)
         with Locations((0, -22.5, 20)):
             Box(42, 5, 40)
         # Central motor pilot hole (22mm diameter)
         Hole(radius=11, depth=10)
         # 4x M3 motor mounting holes on 31mm square pattern
         with Locations((15.5, 15.5, 0), (-15.5, 15.5, 0), (15.5, -15.5, 0), (-15.5, -15.5, 0)):
             Hole(radius=1.6, depth=10)
         # M4 base mounting holes
         with Locations((13, -22.5, 30), (-13, -22.5, 30)):
             Hole(radius=2.2, depth=10)

     if 'show_object' in globals():
         show_object(mount)
  2. Set "is2D": false
  3. Use 3D feature types in "features": "box", "cylinder", "sphere", "cone", "torus", "tube", "plate", "bolt", "gear", "hole", "bracket"

You must respond ONLY with a valid JSON object matching this schema:
{
  "name": "Human-readable Model Name",
  "description": "Short explanation of the CAD geometry and parameters",
  "is2D": boolean,
  "cadCode": "Complete, valid Python code with imports (from build123d import *), dimensions, operations, and export",
  "dimensions": { "width": number, "height": number, "depth": number },
  "features": [
    {
      "type": "box" | "cylinder" | "sphere" | "cone" | "torus" | "tube" | "plate" | "bolt" | "gear" | "hole" | "bracket" | "rectangle_2d" | "circle_2d" | "polygon_2d" | "slot_2d",
      "operation": "add" | "cut" | "subtract",
      "params": {
        "width": number, "height": number, "depth": number,
        "radius": number, "radiusTop": number, "radiusBottom": number,
        "diameter": number, "thickness": number, "segments": number
      },
      "position": [x, y, z],
      "rotation": [rx, ry, rz]
    }
  ]
}

JSON FORMATTING REQUIREMENT:
Respond ONLY with valid JSON. All newlines inside the "cadCode" string MUST be properly escaped as \\n. DO NOT output raw unescaped newlines inside JSON strings.`;

/**
 * Detects if a user prompt is asking for a 2D sketch/drawing rather than a 3D solid
 */
export function is2DPrompt(prompt: string): boolean {
  const lower = prompt.toLowerCase();
  const has2DKeyword = /\b(2d|sketch|drawing|flat|profile|planar|blueprint|cross section|contour)\b/.test(lower);
  const has2DShape = /\b(rectangle|circle|square|ellipse|polygon|slot|arc|line)\b/.test(lower);
  const has3DKeyword = /\b(3d|extrude|extrusion|depth|thickness|enclosure|flange|cube|solid|pipe|boss|bosses|cavity|chamfer|fillet|mating|assembly)\b/.test(lower);

  if (has2DKeyword && !has3DKeyword) return true;
  if (has2DShape && !has3DKeyword && !/\b(height\s*=\s*\d+|standing\s*\d+\s*mm|tall)\b/.test(lower)) return true;
  if (lower.startsWith('draw a ') || lower.startsWith('draw ') || lower.startsWith('sketch a ') || lower.startsWith('sketch ')) {
    if (!has3DKeyword && !lower.includes('box') && !lower.includes('cube') && !lower.includes('enclosure') && !lower.includes('flange')) {
      return true;
    }
  }
  return false;
}

export function detectProvider(apiKey: string, modelName: string = '', customUrl: string = ''): string {
  const key = apiKey.trim();
  const url = customUrl.trim().toLowerCase();
  const model = modelName.trim().toLowerCase();

  if (url.includes('openrouter')) return 'openrouter';
  if (url.includes('deepseek')) return 'deepseek';
  if (url.includes('groq')) return 'groq';
  if (url.includes('anthropic')) return 'anthropic';
  if (url.includes('googleapis')) return 'gemini';
  if (url && !url.includes('openai.com')) return 'custom';

  if (key.startsWith('AIzaSy')) return 'gemini';
  if (key.startsWith('sk-ant-')) return 'anthropic';
  if (key.startsWith('sk-or-')) return 'openrouter';
  if (key.startsWith('gsk_')) return 'groq';

  if (model.includes('gemini')) return 'gemini';
  if (model.includes('claude')) return 'anthropic';
  if (model.includes('deepseek')) return 'deepseek';

  return 'openai';
}

export async function generateCadWithAI(
  prompt: string,
  apiKey: string,
  modelName: string = '',
  provider: string = 'auto',
  customBaseUrl: string = '',
  designHistory: { prompt: string; code: string }[] = []
): Promise<ModelSpecification> {
  const cleanKey = apiKey.trim();
  const activeProvider = provider === 'auto' ? detectProvider(cleanKey, modelName, customBaseUrl) : provider;

  const promptIs2D = is2DPrompt(prompt);

  let historyContext = '';
  if (designHistory.length > 0) {
    historyContext =
      `\nRecent design iterations:\n` +
      designHistory.slice(-3).map((h, i) => `Iteration ${i + 1}: Prompt: "${h.prompt}"`).join('\n');
  }

  const userPrompt =
    `Generate a comprehensive, production-grade CAD design for: "${prompt}".\n` +
    (promptIs2D
      ? `CRITICAL REQUIREMENT: This is a 2D drawing / sketch. Generate complete, detailed Build123d BuildSketch() code with all geometric contours, polar arrays, cutouts, and dimensions. DO NOT output trivial 2-line code. Set "is2D": true, and depth = 0.\n`
      : `CRITICAL REQUIREMENT: This is a 3D solid model. Generate complete, detailed Build123d BuildPart() code with all structural plates, holes, cutouts, fillets, and dimensions. DO NOT output trivial 2-line code. Set "is2D": false.\n`) +
    `${historyContext}\nRespond ONLY with the complete JSON object. Ensure all newlines inside "cadCode" are escaped as \\n.`;

  let rawResponseText = '';

  if (activeProvider === 'gemini') {
    rawResponseText = await callGeminiAPI(cleanKey, modelName || 'gemini-2.0-flash', userPrompt);
  } else if (activeProvider === 'anthropic') {
    rawResponseText = await callAnthropicAPI(cleanKey, modelName || 'claude-3-5-sonnet-20241022', userPrompt, customBaseUrl);
  } else {
    // OpenAI, OpenRouter, DeepSeek, Groq, or Custom OpenAI-compatible
    let defaultEndpoint = 'https://api.openai.com/v1';
    let defaultModel = modelName || 'gpt-4o';

    if (activeProvider === 'openrouter') {
      defaultEndpoint = 'https://openrouter.ai/api/v1';
      defaultModel = modelName || 'anthropic/claude-3.5-sonnet';
    } else if (activeProvider === 'deepseek') {
      defaultEndpoint = 'https://api.deepseek.com/v1';
      defaultModel = modelName || 'deepseek-chat';
    } else if (activeProvider === 'groq') {
      defaultEndpoint = 'https://api.groq.com/openai/v1';
      defaultModel = modelName || 'llama-3.3-70b-versatile';
    } else if (activeProvider === 'custom') {
      defaultEndpoint = customBaseUrl || 'http://localhost:11434/v1';
      defaultModel = modelName || 'llama3';
    }

    const endpoint = customBaseUrl ? customBaseUrl.replace(/\/$/, '') : defaultEndpoint;
    rawResponseText = await callOpenAICompatibleAPI(cleanKey, defaultModel, userPrompt, endpoint);
  }

  return parseCadSpecification(rawResponseText, prompt);
}

/**
 * Direct Google Gemini API Call
 */
async function callGeminiAPI(apiKey: string, model: string, userPrompt: string): Promise<string> {
  if (!apiKey) throw new Error('API Key is required for Gemini.');
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ role: 'user', parts: [{ text: `${CAD_SYSTEM_INSTRUCTION}\n\n${userPrompt}` }] }],
      generationConfig: {
        temperature: 0.2,
        topP: 0.95,
        maxOutputTokens: 4096,
        responseMimeType: 'application/json',
      },
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error?.message || `Gemini API Error: HTTP ${response.status}`);
  }

  const data = await response.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error('No response returned from Gemini API.');
  return text;
}

/**
 * OpenAI-compatible API Call (OpenAI, OpenRouter, DeepSeek, Groq, Ollama, etc.)
 */
async function callOpenAICompatibleAPI(
  apiKey: string,
  model: string,
  userPrompt: string,
  baseUrl: string
): Promise<string> {
  const url = baseUrl.endsWith('/chat/completions') ? baseUrl : `${baseUrl}/chat/completions`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }

  const bodyPayload: any = {
    model: model,
    messages: [
      { role: 'system', content: CAD_SYSTEM_INSTRUCTION },
      { role: 'user', content: userPrompt },
    ],
    temperature: 0.2,
    max_tokens: 4096,
  };

  // Enable JSON object response format where supported
  if (!baseUrl.includes('anthropic') && !baseUrl.includes('claude')) {
    bodyPayload.response_format = { type: 'json_object' };
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(bodyPayload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error?.message || err.message || `API Error: HTTP ${response.status} from ${baseUrl}`);
  }

  const data = await response.json();
  const content = data.choices?.[0]?.message?.content;
  if (!content) throw new Error('No content returned in chat completion response.');
  return content;
}

/**
 * Anthropic Claude API Call
 */
async function callAnthropicAPI(
  apiKey: string,
  model: string,
  userPrompt: string,
  customUrl: string = ''
): Promise<string> {
  const url = customUrl
    ? customUrl.endsWith('/messages')
      ? customUrl
      : `${customUrl}/messages`
    : 'https://api.anthropic.com/v1/messages';

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'dangerously-allow-browser': 'true',
    },
    body: JSON.stringify({
      model: model,
      max_tokens: 4096,
      system: CAD_SYSTEM_INSTRUCTION,
      messages: [{ role: 'user', content: userPrompt }],
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error?.message || `Anthropic API Error: HTTP ${response.status}`);
  }

  const data = await response.json();
  const content = data.content?.[0]?.text;
  if (!content) throw new Error('No content returned from Anthropic API.');
  return content;
}

/**
 * Repairs unescaped control characters and raw newlines inside JSON string literals
 */
function repairJsonString(jsonStr: string): string {
  let inString = false;
  let isEscaped = false;
  let result = '';

  for (let i = 0; i < jsonStr.length; i++) {
    const char = jsonStr[i];

    if (inString) {
      if (char === '\\') {
        isEscaped = !isEscaped;
        result += char;
      } else if (char === '"' && !isEscaped) {
        inString = false;
        result += char;
      } else if (char === '\n') {
        result += '\\n';
      } else if (char === '\r') {
        // remove carriage returns
      } else if (char === '\t') {
        result += '\\t';
      } else {
        result += char;
      }
      if (char !== '\\') {
        isEscaped = false;
      }
    } else {
      if (char === '"') {
        inString = true;
      }
      result += char;
    }
  }
  return result;
}

/**
 * Extracts pure Python code from markdown blocks or raw text
 */
function extractPythonCode(text: string): string | null {
  const match = text.match(/```(?:python|py)?\s*([\s\S]*?)```/i);
  if (match && match[1].trim().length > 15) {
    return match[1].trim();
  }
  if (
    text.includes('from build123d') ||
    text.includes('import cadquery') ||
    text.includes('BuildPart') ||
    text.includes('BuildSketch')
  ) {
    return text.trim();
  }
  return null;
}

/**
 * Resilient, Infallible Multi-Layer JSON & Python CAD Parser
 * Never throws an unhandled error; gracefully reconstructs valid models from any format.
 */
export function parseCadSpecification(rawText: string, originalPrompt: string): ModelSpecification {
  let cleaned = rawText.trim();
  if (cleaned.startsWith('```json')) {
    cleaned = cleaned.replace(/^```json\s*/, '').replace(/\s*```$/, '');
  } else if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```\s*/, '').replace(/\s*```$/, '');
  }

  let parsed: any = null;

  // Stage 1: Direct JSON parse
  try {
    parsed = JSON.parse(cleaned);
  } catch {
    // Stage 2: Repaired JSON parse (handling unescaped newlines in cadCode)
    try {
      parsed = JSON.parse(repairJsonString(cleaned));
    } catch {
      // Stage 3: Substring extraction between first { and last }
      const firstBrace = cleaned.indexOf('{');
      const lastBrace = cleaned.lastIndexOf('}');
      if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
        const sub = cleaned.substring(firstBrace, lastBrace + 1);
        try {
          parsed = JSON.parse(repairJsonString(sub));
        } catch {
          // Continue to Stage 4
        }
      }
    }
  }

  // Stage 4: Regex-based field extraction if JSON object was malformed
  if (!parsed || typeof parsed !== 'object') {
    const nameMatch = cleaned.match(/"name"\s*:\s*"([^"]+)"/i);
    const descMatch = cleaned.match(/"description"\s*:\s*"([^"]+)"/i);
    const is2DMatch = cleaned.match(/"is2D"\s*:\s*(true|false)/i);

    let extractedCode = extractPythonCode(cleaned);

    if (extractedCode || nameMatch) {
      parsed = {
        name: nameMatch ? nameMatch[1] : (is2DPrompt(originalPrompt) ? '2D Technical Drawing' : 'TextCAD Design'),
        description: descMatch ? descMatch[1] : originalPrompt,
        is2D: is2DMatch ? is2DMatch[1] === 'true' : is2DPrompt(originalPrompt),
        cadCode: extractedCode,
      };
    }
  }

  // Stage 5: Pure Python Code fallback
  if (!parsed || !parsed.cadCode) {
    const pyCode = extractPythonCode(rawText);
    const promptIs2D = is2DPrompt(originalPrompt);

    if (pyCode) {
      parsed = {
        name: promptIs2D ? '2D CAD Sketch' : 'Parametric CAD Model',
        description: originalPrompt,
        cadCode: pyCode,
        is2D: promptIs2D || (pyCode.includes('BuildSketch') && !pyCode.includes('extrude')),
      };
    } else {
      // Stage 6: Direct prompt synthesis fallback
      parsed = synthesizeModelFromPrompt(originalPrompt);
    }
  }

  // Determine final is2D flag
  const finalIs2D =
    parsed.is2D === true ||
    is2DPrompt(originalPrompt) ||
    (parsed.cadCode && parsed.cadCode.includes('BuildSketch') && !parsed.cadCode.includes('extrude'));

  // Ensure valid Python CAD code is present
  const finalCadCode =
    parsed.cadCode ||
    (finalIs2D
      ? `# 2D Technical CAD Drawing\nfrom build123d import *\n\nwith BuildSketch() as sketch:\n    Rectangle(100, 50)\n\nif 'show_object' in globals():\n    show_object(sketch)\n`
      : `# 3D CAD Solid Model\nfrom build123d import *\n\nwith BuildPart() as part:\n    Box(100, 60, 30)\n\nif 'show_object' in globals():\n    show_object(part)\n`);

  // Resolve features
  let finalFeatures: GeometricFeature[] = Array.isArray(parsed.features) && parsed.features.length > 0
    ? parsed.features
    : parseFeaturesFromCode(finalCadCode, originalPrompt);

  return {
    name: parsed.name || (finalIs2D ? '2D Technical Drawing' : 'TextCAD Model'),
    description: parsed.description || originalPrompt,
    is2D: finalIs2D,
    cadCode: finalCadCode,
    dimensions: parsed.dimensions || {
      width: 100,
      height: finalIs2D ? 50 : 30,
      depth: finalIs2D ? 0 : 60,
    },
    features: finalFeatures,
  };
}

/**
 * Synthesizes a valid ModelSpecification directly from a user prompt when AI response is unstructured
 */
function synthesizeModelFromPrompt(prompt: string): any {
  const is2D = is2DPrompt(prompt);

  if (is2D) {
    const pRect = prompt.match(/(\d+)\s*(?:x|by|\*|\s+)\s*(\d+)/i);
    const w = pRect ? parseFloat(pRect[1]) : 100;
    const h = pRect ? parseFloat(pRect[2]) : 50;

    return {
      name: '2D Technical Sketch',
      description: prompt,
      is2D: true,
      cadCode: `from build123d import *\n\nwith BuildSketch() as sketch:\n    Rectangle(${w}, ${h})\n\nif 'show_object' in globals():\n    show_object(sketch)\n`,
      dimensions: { width: w, height: h, depth: 0 },
      features: [{ type: 'rectangle_2d', params: { width: w, height: h }, position: [0, 0, 0] }],
    };
  }

  // 3D Model
  return {
    name: 'Parametric CAD Model',
    description: prompt,
    is2D: false,
    cadCode: `from build123d import *\n\nwith BuildPart() as part:\n    Box(100, 60, 30)\n\nif 'show_object' in globals():\n    show_object(part)\n`,
    dimensions: { width: 100, height: 30, depth: 60 },
    features: [{ type: 'box', params: { width: 100, height: 30, depth: 60 }, position: [0, 15, 0] }],
  };
}

/**
 * Universal API Key Connection Test
 */
export async function testAIConnection(
  apiKey: string,
  modelName: string = '',
  provider: string = 'auto',
  customUrl: string = ''
): Promise<{ valid: boolean; error?: string; detected?: string }> {
  try {
    const key = apiKey.trim();
    const activeProvider = provider === 'auto' ? detectProvider(key, modelName, customUrl) : provider;

    if (activeProvider === 'gemini') {
      const model = modelName || 'gemini-2.0-flash';
      const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: 'Respond with READY' }] }],
          generationConfig: { maxOutputTokens: 10 },
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return { valid: false, error: err.error?.message || `HTTP ${res.status}`, detected: 'Google Gemini' };
      }
      return { valid: true, detected: 'Google Gemini' };
    }

    if (activeProvider === 'anthropic') {
      const model = modelName || 'claude-3-5-sonnet-20241022';
      const url = customUrl || 'https://api.anthropic.com/v1/messages';
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': key,
          'anthropic-version': '2023-06-01',
          'dangerously-allow-browser': 'true',
        },
        body: JSON.stringify({
          model,
          max_tokens: 10,
          messages: [{ role: 'user', content: 'Say READY' }],
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return { valid: false, error: err.error?.message || `HTTP ${res.status}`, detected: 'Anthropic Claude' };
      }
      return { valid: true, detected: 'Anthropic Claude' };
    }

    // OpenAI / OpenAI-compatible / Custom
    let base =
      customUrl ||
      (activeProvider === 'openrouter'
        ? 'https://openrouter.ai/api/v1'
        : activeProvider === 'deepseek'
        ? 'https://api.deepseek.com/v1'
        : activeProvider === 'groq'
        ? 'https://api.groq.com/openai/v1'
        : 'https://api.openai.com/v1');
    const url = base.endsWith('/chat/completions') ? base : `${base}/chat/completions`;
    const model =
      modelName ||
      (activeProvider === 'deepseek'
        ? 'deepseek-chat'
        : activeProvider === 'groq'
        ? 'llama-3.3-70b-versatile'
        : 'gpt-4o-mini');

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(key ? { Authorization: `Bearer ${key}` } : {}),
      },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: 'Say READY' }],
        max_tokens: 10,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { valid: false, error: err.error?.message || err.message || `HTTP ${res.status}`, detected: activeProvider };
    }

    return { valid: true, detected: activeProvider };
  } catch (e: any) {
    return { valid: false, error: e.message || 'Connection failed' };
  }
}
