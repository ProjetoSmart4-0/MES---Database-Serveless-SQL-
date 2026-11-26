const API_BASE_KEY = "smart40_mes_api_base";
const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const COLORS = ["PRETA", "VERMELHA", "BRANCA", "AMARELA", "VERDE", "AZUL"];
const BLOCK_SIZES = {UNICO:1, DUPLO:2, TRIPLO:3};
let inventory = [], orders = [];
const $ = id => document.getElementById(id);
const apiBase = () => (localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE).replace(/\/+$/, "");
function showToast(message) { const toast=$("toast"); toast.textContent=message; toast.classList.add("show"); setTimeout(()=>toast.classList.remove("show"),2800); }
function setConnection(ok, detail="") {
  $("connectionPulse").style.background=ok?"var(--green)":"var(--orange)";
  $("connectionLabel").textContent=ok?"API conectada":"Não conectada";
  $("connectionDetail").textContent=detail||(ok?apiBase():"Verifique o FastAPI e o endereço");
  $("apiState").textContent=ok?"Conectada":"Sem conexão"; $("apiState").className="integration-state "+(ok?"ok":"");
  $("dbState").textContent=ok?"Via API":"Aguardando"; $("dbState").className="integration-state "+(ok?"ok":"");
}
function escapeHtml(value) { return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function formatDate(value) { if(!value)return "—"; const d=new Date(value); return Number.isNaN(d.getTime())?value:d.toLocaleString("pt-BR"); }
function colorLabel(c) { return ({PRETA:"Preta",VERMELHA:"Vermelha",BRANCA:"Branca",AMARELA:"Amarela",VERDE:"Verde",AZUL:"Azul"})[c]||c||"—"; }
function statusLabel(s) { return ({PENDING:"Pendente",IN_PROGRESS:"Em andamento",COMPLETED:"Concluída",CANCELLED:"Cancelada",FAILED:"Falhou"})[s]||s||"—"; }
function renderInventory() {
  const q=($("searchInventory").value||"").toLowerCase(); const rows=inventory.filter(x=>(x.item_name+" "+x.color).toLowerCase().includes(q));
  $("recordCount").textContent=`${rows.length} REGISTROS`; $("navStockCount").textContent=String(inventory.length).padStart(2,"0");
  $("inventoryRows").innerHTML=rows.map(x=>`<tr><td><strong>${escapeHtml(x.item_name)}</strong></td><td>${colorLabel(x.color)}</td><td><strong>${x.current_quantity} ${escapeHtml(x.unit)}</strong></td><td><span class="status-pill status-neutral">Capacidade fixa</span></td></tr>`).join("")||'<tr><td colspan="4" class="empty">Nenhum componente encontrado.</td></tr>';
  $("overviewInventory").innerHTML=inventory.slice(0,5).map(x=>`<tr><td><strong>${escapeHtml(x.item_name)}</strong></td><td>${colorLabel(x.color)}</td><td>${x.current_quantity}</td><td><span class="status-pill status-neutral">Fixo</span></td></tr>`).join("");
  $("metricItems").textContent=inventory.length; $("metricUnits").textContent=inventory.reduce((s,x)=>s+Number(x.current_quantity),0).toLocaleString("pt-BR"); $("metricAlerts").textContent="Fixo";
  $("tableMessage").textContent=`Capacidade consultada: ${new Date().toLocaleTimeString("pt-BR")}`;
}
async function loadInventory() {
  try { const r=await fetch(`${apiBase()}/api/v1/mes/inventory`); const j=await r.json(); if(!r.ok)throw Error(j.detail||`HTTP ${r.status}`); inventory=j.data||[]; setConnection(true); renderInventory(); }
  catch(e){setConnection(false,e.message);$("inventoryRows").innerHTML=`<tr><td colspan="4" class="empty">Falha ao carregar: ${escapeHtml(e.message)}</td></tr>`;$("overviewInventory").innerHTML='<tr><td colspan="4" class="empty">API indisponível.</td></tr>';$("tableMessage").textContent=e.message;}
}
function renderBoxCustomizations() {
  const count=BLOCK_SIZES[$("blockType").value]||1;
  $("boxCustomizations").innerHTML=Array.from({length:count},(_,i)=>`<fieldset class="box-config"><legend>Caixinha ${i+1}</legend><div class="plaque-grid">${[1,2,3].map(n=>`<label>Plaquinha ${n}<select class="plaque-color" data-box="${i+1}" data-plaque="${n}">${COLORS.map(c=>`<option value="${c}">${colorLabel(c)}</option>`).join("")}</select></label>`).join("")}</div></fieldset>`).join("");
}
function collectBoxes() { const count=BLOCK_SIZES[$("blockType").value]; return Array.from({length:count},(_,i)=>({plaque_colors:[1,2,3].map(n=>document.querySelector(`.plaque-color[data-box="${i+1}"][data-plaque="${n}"]`).value)})); }
function validateLocalCapacity(boxes) {
  const usage={}; boxes.forEach(b=>b.plaque_colors.forEach(c=>usage[c]=(usage[c]||0)+1));
  const exceeded=Object.entries(usage).filter(([,n])=>n>10);
  return exceeded.length?`Capacidade fixa excedida: ${exceeded.map(([c,n])=>`${colorLabel(c)} (${n}/10)`).join(", ")}.`:
    (boxes.length>3?"A máquina aceita no máximo três caixinhas por pedido.":"");
}
function boxesSummary(boxes) {
  if (!Array.isArray(boxes) || !boxes.length) return "—";
  return boxes.map(b => `Cx ${b.box_number}: ${[b.plaque_color_1,b.plaque_color_2,b.plaque_color_3].map(colorLabel).join(" / ")}`).join("<br>");
}
function renderOrders() {
  $("ordersCount").textContent=`${orders.length} ORDENS`;
  $("ordersRows").innerHTML=orders.map(o=>`<tr><td><strong>${escapeHtml(o.order_number)}</strong><small class="order-id">ID ${o.id}</small></td><td>${({UNICO:"Único",DUPLO:"Duplo",TRIPLO:"Triplo",LEGADO:"Legado"})[o.block_type]||o.block_type||"—"}</td><td>${colorLabel(o.base_color||o.lid_color)}</td><td>${o.target_quantity??0}<small class="order-id">${boxesSummary(o.boxes)}</small></td><td>${o.produced_quantity??0}</td><td>${o.defective_quantity??0}</td><td><span class="status-pill ${o.status==="COMPLETED"?"status-ok":o.status==="CANCELLED"||o.status==="FAILED"?"status-low":"status-neutral"}">${statusLabel(o.status)}</span></td><td>${formatDate(o.created_at)}</td></tr>`).join("")||'<tr><td colspan="8" class="empty">Nenhuma ordem cadastrada ainda.</td></tr>';
}
async function loadOrders() {
  $("ordersRows").innerHTML='<tr><td colspan="8" class="empty">Consultando API…</td></tr>';
  try { const r=await fetch(`${apiBase()}/api/v1/mes/orders`);const j=await r.json();if(!r.ok)throw Error(j.detail||`HTTP ${r.status}`);orders=j.data||[];renderOrders(); }
  catch(e){$("ordersRows").innerHTML=`<tr><td colspan="8" class="empty">Erro ao carregar ordens: ${escapeHtml(e.message)}</td></tr>`;}
}
async function createOrder(event) {
  event.preventDefault(); const feedback=$("orderFeedback");feedback.className="feedback";feedback.textContent="";
  const payload={block_type:$("blockType").value,base_color:$("baseColor").value,boxes:collectBoxes()};
  const localError=validateLocalCapacity(payload.boxes);if(localError){feedback.className="feedback error";feedback.textContent=localError;return;}
  try { const r=await fetch(`${apiBase()}/api/v1/mes/orders`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});const j=await r.json();if(!r.ok)throw Error(j.detail||`HTTP ${r.status}`);
    feedback.textContent=`OP ${j.data.order_number} criada com ${j.data.target_quantity} caixinha(s). ID: ${j.data.id}.`;showToast("Pedido enviado e OP gerada automaticamente.");await loadOrders();
  } catch(e){feedback.className="feedback error";feedback.textContent=`Não foi possível criar o pedido: ${e.message}`;}
}
async function processPiece(event) {
  event.preventDefault();const feedback=$("pieceFeedback");feedback.className="feedback";feedback.textContent="";
  const id=Number($("pieceOrderId").value),qr_code=$("pieceQrCode").value.trim();if(!Number.isInteger(id)||id<=0||!qr_code){feedback.className="feedback error";feedback.textContent="Informe o ID da OP e um QR Code.";return;}
  try {const r=await fetch(`${apiBase()}/api/v1/mes/orders/${id}/pieces`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({qr_code})});const j=await r.json();if(!r.ok)throw Error(j.detail||`HTTP ${r.status}`);feedback.textContent=`Caixinha ${j.data.caixinha.box_number} registrada. Produzidas: ${j.data.produced_quantity}/${orders.find(o=>o.id===id)?.target_quantity||"—"}.`;showToast("Rastreabilidade registrada; capacidade fixa preservada.");$("pieceQrCode").value="";await loadOrders();}
  catch(e){feedback.className="feedback error";feedback.textContent=`Falha no processamento: ${e.message}`;}
}
function navigate(page){document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));$(`page-${page}`).classList.add("active");document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.page===page));const names={overview:"Visão geral",inventory:"Estoque",orders:"Ordens de produção",oee:"Indicadores OEE"};$("crumb").textContent=names[page];if(page==="orders")loadOrders();}
document.querySelectorAll(".nav-item").forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.page)));
document.querySelectorAll("[data-goto]").forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.goto)));
$("refreshOverview").addEventListener("click",loadInventory);$("refreshInventory").addEventListener("click",loadInventory);$("refreshOrders").addEventListener("click",loadOrders);$("searchInventory").addEventListener("input",renderInventory);
$("blockType").addEventListener("change",renderBoxCustomizations);$("orderForm").addEventListener("submit",createOrder);$("pieceForm").addEventListener("submit",processPiece);
$("clock").textContent=new Date().toLocaleTimeString("pt-BR");setInterval(()=>$("clock").textContent=new Date().toLocaleTimeString("pt-BR"),1000);
renderBoxCustomizations();loadInventory();
