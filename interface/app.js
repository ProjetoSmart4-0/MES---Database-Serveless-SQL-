const API_BASE_KEY = "smart40_mes_api_base";
const DEFAULT_API_BASE = "http://127.0.0.1:8000";
let inventory = [];
const $ = (id) => document.getElementById(id);
const apiBase = () => (localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE).replace(/\/+$/, "");

function showToast(message) {
  const toast = $("toast"); toast.textContent = message; toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2800);
}
function setConnection(ok, detail = "") {
  $("connectionPulse").style.background = ok ? "var(--green)" : "var(--orange)";
  $("connectionLabel").textContent = ok ? "API conectada" : "Não conectada";
  $("connectionDetail").textContent = detail || (ok ? apiBase() : "Verifique o FastAPI e o endereço");
  $("apiState").textContent = ok ? "Conectada" : "Sem conexão";
  $("apiState").className = "integration-state " + (ok ? "ok" : "");
  $("dbState").textContent = ok ? "Via API" : "Aguardando";
  $("dbState").className = "integration-state " + (ok ? "ok" : "");
}
function categoryLabel(value) {
  return ({RAW_MATERIAL:"Matéria-prima",IN_PROCESSING:"Em processamento",INSPECTED_OK:"Inspecionado OK",INSPECTED_NOK:"Inspecionado NOK",EXPEDITED:"Expedição"})[value] || value || "—";
}
function statusFor(item) {
  const q = Number(item.quantity || 0), min = Number(item.reorder_point || 0);
  return q <= min ? ["Reposição", "status-low"] : ["Disponível", "status-ok"];
}
function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("pt-BR");
}
function renderInventory() {
  const query = ($("searchInventory")?.value || "").toLowerCase();
  const filtered = inventory.filter(x => (x.item_name || "").toLowerCase().includes(query));
  $("recordCount").textContent = `${filtered.length} REGISTROS`;
  $("navStockCount").textContent = String(inventory.length).padStart(2,"0");
  $("inventoryRows").innerHTML = filtered.length ? filtered.map(item => {
    const [label, cls] = statusFor(item);
    return `<tr><td>${item.id ?? "—"}</td><td><strong>${escapeHtml(item.item_name)}</strong></td><td>${categoryLabel(item.category)}</td><td><strong>${item.quantity ?? 0}</strong></td><td>${item.reorder_point ?? 0}</td><td>${formatDate(item.updated_at)}</td><td><span class="status-pill ${cls}">${label}</span></td></tr>`;
  }).join("") : `<tr><td colspan="7" class="empty">Nenhum item encontrado.</td></tr>`;
  $("overviewInventory").innerHTML = inventory.length ? inventory.slice(0,5).map(item => {
    const [label, cls] = statusFor(item);
    return `<tr><td><strong>${escapeHtml(item.item_name)}</strong></td><td>${categoryLabel(item.category)}</td><td>${item.quantity ?? 0}</td><td><span class="status-pill ${cls}">${label}</span></td></tr>`;
  }).join("") : `<tr><td colspan="4" class="empty">Nenhum dado recebido.</td></tr>`;
  $("metricItems").textContent = inventory.length;
  $("metricUnits").textContent = inventory.reduce((sum,x)=>sum+Number(x.quantity||0),0).toLocaleString("pt-BR");
  $("metricAlerts").textContent = inventory.filter(x=>Number(x.quantity||0)<=Number(x.reorder_point||0)).length;
  $("debitItem").innerHTML = `<option value="">Selecione um item</option>` + inventory.map(x=>`<option value="${escapeAttr(x.item_name)}">${escapeHtml(x.item_name)} — ${x.quantity} un.</option>`).join("");
  $("tableMessage").textContent = `Última consulta: ${new Date().toLocaleTimeString("pt-BR")}`;
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function escapeAttr(value) { return escapeHtml(value); }

async function loadInventory() {
  $("tableMessage").textContent = "Consultando API…";
  try {
    const response = await fetch(`${apiBase()}/api/v1/mes/inventory`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    if (!Array.isArray(result.data)) throw new Error("A resposta não contém uma lista em data.");
    inventory = result.data;
    setConnection(true, apiBase());
    renderInventory();
  } catch (error) {
    setConnection(false, error.message);
    $("inventoryRows").innerHTML = `<tr><td colspan="7" class="empty">Não foi possível carregar. Confira se o FastAPI está rodando e se o CORS foi configurado.</td></tr>`;
    $("overviewInventory").innerHTML = `<tr><td colspan="4" class="empty">API indisponível.</td></tr>`;
    $("tableMessage").textContent = `Falha: ${error.message}`;
    $("metricItems").textContent = "—"; $("metricUnits").textContent = "—"; $("metricAlerts").textContent = "—";
  }
}
async function debitStock(event) {
  event.preventDefault();
  const item = $("debitItem").value;
  const quantity = Number($("debitQuantity").value);
  const feedback = $("debitFeedback");
  feedback.className = "feedback"; feedback.textContent = "";
  if (!item || !Number.isInteger(quantity) || quantity <= 0) {
    feedback.className = "feedback error"; feedback.textContent = "Selecione um item e informe uma quantidade inteira maior que zero."; return;
  }
  try {
    const url = `${apiBase()}/api/v1/mes/inventory/debit?item_name=${encodeURIComponent(item)}&quantity=${quantity}`;
    const response = await fetch(url, {method:"POST"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    feedback.textContent = result.message || "Baixa realizada.";
    showToast("Baixa registrada com sucesso.");
    await loadInventory();
  } catch(error) {
    feedback.className = "feedback error"; feedback.textContent = `Não foi possível registrar: ${error.message}`;
  }
}
function navigate(page) {
  document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));
  $(`page-${page}`).classList.add("active");
  document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.page===page));
  const names = {overview:"Visão geral",inventory:"Estoque",orders:"Ordens de produção",oee:"Indicadores OEE"};
  $("crumb").textContent = names[page];
}
document.querySelectorAll(".nav-item").forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.page)));
document.querySelectorAll("[data-goto]").forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.goto)));
$("refreshOverview").addEventListener("click",loadInventory);
$("refreshInventory").addEventListener("click",loadInventory);
$("searchInventory").addEventListener("input",renderInventory);
$("debitForm").addEventListener("submit",debitStock);
$("clock").textContent = new Date().toLocaleTimeString("pt-BR");
setInterval(()=>{$("clock").textContent=new Date().toLocaleTimeString("pt-BR")},1000);
loadInventory();
