import { API_BASE_URL } from "./config";

async function parseJsonResponse(response) {
  let body;

  try {
    body = await response.json();
  } catch {
    throw new Error(`Server returned an unexpected response (status ${response.status}).`);
  }

  if (!response.ok) {
    throw new Error(body.error || `Request failed (status ${response.status}).`);
  }

  return body;
}

function buildImageFormField(asset, fieldName) {
  const formData = new FormData();
  const name = asset.fileName || `${fieldName}.jpg`;
  const type = asset.mimeType || "image/jpeg";

  formData.append(fieldName, {
    uri: asset.uri,
    name,
    type,
  });

  return formData;
}

export async function scanReceipt(asset, knownMedications) {
  const formData = buildImageFormField(asset, "receipt");
  formData.append("known_medications", JSON.stringify(knownMedications || []));

  const response = await fetch(`${API_BASE_URL}/api/scan`, {
    method: "POST",
    body: formData,
  });

  return parseJsonResponse(response);
}

export async function scanMedication(asset, knownGroceries) {
  const formData = buildImageFormField(asset, "medication");
  formData.append("known_groceries", JSON.stringify(knownGroceries || []));

  const response = await fetch(`${API_BASE_URL}/api/scan-medication`, {
    method: "POST",
    body: formData,
  });

  return parseJsonResponse(response);
}

export async function getRecipe(ingredients) {
  const response = await fetch(`${API_BASE_URL}/api/recipe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingredients }),
  });

  return parseJsonResponse(response);
}
