import axios from "axios";

export const getApiBaseUrl = () => import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: getApiBaseUrl(),
});

export const documentFileUrl = (documentId) => `${getApiBaseUrl()}/documents/${documentId}/file`;

export const extractDocument = async (file, requestId) => {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/extract", form, {
    headers: requestId ? { "x-request-id": requestId } : undefined,
  });
  return data;
};

export const listDocuments = async (limit = 100) => {
  const { data } = await api.get("/documents", { params: { limit } });
  return data;
};

export const queryDocument = async (question, documentId) => {
  const body = { question };
  if (documentId) body.document_id = documentId;
  const { data } = await api.post("/query", body);
  return data;
};

export const getExtractionStatus = async (requestId) => {
  const { data } = await api.get(`/extract/status/${requestId}`);
  return data;
};
