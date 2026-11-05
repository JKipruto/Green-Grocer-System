const CART_KEY = "greenbasket_cart";
let cart = [];
try { cart = JSON.parse(localStorage.getItem(CART_KEY) || "[]"); } catch { cart = []; }
function saveCart(){ localStorage.setItem(CART_KEY, JSON.stringify(cart)); renderCartCount(); }
function renderCartCount(){
  const el = document.getElementById("cart-count");
  if(el) el.textContent = cart.reduce((sum,item)=>sum+item.quantity,0);
}
function addToCart(id,name,price,stock,image){
  if(!window.CURRENT_USER){ window.location.href="/login"; return; }
  const found=cart.find(x=>x.id===id);
  if(found){ if(found.quantity>=stock){alert("That is all the available stock.");return;} found.quantity++; }
  else cart.push({id,name,price,stock,image,quantity:1});
  saveCart(); openCart();
}
function openCart(){ const modal=document.getElementById("cart-modal"); if(modal){modal.classList.add("open");renderCart();} }
function closeCart(){document.getElementById("cart-modal")?.classList.remove("open");}
function changeQty(id,delta){
  const item=cart.find(x=>x.id===id); if(!item)return;
  item.quantity=Math.min(item.stock,item.quantity+delta);
  if(item.quantity<=0)cart=cart.filter(x=>x.id!==id);
  saveCart();renderCart();
}
function removeItem(id){cart=cart.filter(x=>x.id!==id);saveCart();renderCart();}
function renderCart(){
  const host=document.getElementById("cart-items"); if(!host)return;
  if(!cart.length){host.innerHTML='<div class="cart-empty">Your basket is looking a little empty. Add some fresh picks!</div>';}
  else host.innerHTML=cart.map(item=>`<div class="cart-line"><div class="cart-thumb">${item.image?`<img src="${escapeHtml(item.image)}" alt="">`:"🥬"}</div><div class="cart-line-info"><b>${escapeHtml(item.name)}</b><small>KSh ${Number(item.price).toFixed(0)} each</small><div class="qty-control"><button onclick="changeQty(${item.id},-1)">−</button><span>${item.quantity}</span><button onclick="changeQty(${item.id},1)">+</button><button class="remove-link" onclick="removeItem(${item.id})">Remove</button></div></div><b>KSh ${(item.price*item.quantity).toFixed(0)}</b></div>`).join("");
  const total=cart.reduce((s,x)=>s+x.price*x.quantity,0);
  document.getElementById("cart-total").textContent="KSh "+total.toFixed(0);
  const checkout=document.querySelector(".checkout-button"); if(checkout)checkout.disabled=!cart.length;
  togglePhone();
}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function togglePhone(){const field=document.getElementById("phone-field"),method=document.getElementById("payment-method");if(field&&method)field.style.display=method.value==="mpesa"?"block":"none";}
async function checkout(){
  const message=document.getElementById("checkout-message"); message.textContent="Processing your order…";
  const method=document.getElementById("payment-method").value;
  const phone=document.getElementById("mpesa-phone").value.trim();
  try{
    const res=await fetch("/api/checkout",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({items:cart.map(x=>({id:x.id,quantity:x.quantity})),payment_method:method,phone})});
    const data=await res.json();
    if(!res.ok || !data.ok){message.textContent=data.message||data.detail||"Could not place order.";return;}
    cart=[];saveCart();renderCart();message.textContent=data.message+" Total: KSh "+Number(data.total).toFixed(2);
    setTimeout(()=>{closeCart();window.location.href="/orders";},3500);
  }catch(e){message.textContent="Network error. Please try again.";}
}
document.addEventListener("DOMContentLoaded",()=>{renderCartCount();togglePhone();});
