// Update navbar berdasarkan login status
function updateNavbar() {
  const user = auth.getCurrentUser();
  const authSection = document.getElementById('authSection');
  const welcomeMessage = document.getElementById('welcomeMessage');

  if (user) {
    // Show welcome message
    welcomeMessage.textContent = `Welcome back, ${user.username}! Ready for some magical concerts?`;
    
    // Update auth section
    authSection.innerHTML = `
      <span>Hello, ${user.username}!</span> | 
      <a href="/account">My Account</a> | 
      <a href="#" onclick="logout()">Logout</a>
    `;
  } else {
    // Show login/register links
    authSection.innerHTML = `
      <a href="/login">Login</a> | 
      <a href="/register">Register</a>
    `;
    welcomeMessage.textContent = '';
  }
}

function logout() {
  if (confirm('Are you sure you want to log out?')) {
    auth.logout();
    window.location.href = "/login"; // redirect ke login page Flask
  }
}

// Panggil saat page load
document.addEventListener('DOMContentLoaded', function() {
  // Check authentication on page load
  if (!auth.isLoggedIn()) {
    window.location.href = '/login'; // redirect kalau belum login
    return;
  }
  
  updateNavbar();
  
  // Add loading animation
  setTimeout(() => {
    document.body.style.opacity = '1';
    document.body.style.transition = 'opacity 0.5s ease';
  }, 100);
});

// PBO JS - Booking System
class Ticket {
  constructor(city, type, price) {
    this.city = city;
    this.type = type;
    this.price = price;
  }
}

class BookingModal {
  constructor(modalId, selectBtnId) {
    this.modal = document.getElementById(modalId);
    this.selectBtn = document.getElementById(selectBtnId);
    this.selectedTicket = null;
    this.selectedCity = null;

    window.addEventListener("click", (event) => {
      if (event.target === this.modal) this.close();
    });
  }

  open(city) {
    // Check if user is logged in
    if (!auth.isLoggedIn()) {
      alert('Please login first to book tickets!');
      window.location.href = '/login'; // ganti ke route Flask
      return;
    }

    this.selectedCity = city;
    const title = document.getElementById("modalTitle");
    const info = document.getElementById("modalInfo");
    const cityData = {
      "Jakarta": ["December 15, 2024","Jakarta Convention Center"],
      "Bandung": ["December 18, 2024","Bandung Convention Hall"],
      "Surabaya": ["December 22, 2024","Surabaya Grand Hall"]
    };

    title.innerText = `Book Tickets - ${city}`;
    info.innerText = `${cityData[city][0]} | ${cityData[city][1]}`;
    this.modal.style.display = "block";

    this.selectedTicket = null;
    document.querySelectorAll('.ticket-card').forEach(card => card.classList.remove('active'));
    this.selectBtn.classList.remove("active");
    this.selectBtn.disabled = true;
  }

  close() { 
    this.modal.style.display = "none"; 
    this.selectedCity = null;
  }

  select(element, type){
    document.querySelectorAll('.ticket-card').forEach(card => card.classList.remove('active'));
    element.classList.add('active');
    this.selectedTicket = type;
    this.selectBtn.classList.add("active");
    this.selectBtn.disabled = false;
  }

  confirm(){
    if(this.selectedTicket && this.selectedCity){
      const ticket = new Ticket(this.selectedCity, this.selectedTicket, this.getPrice(this.selectedTicket));
      // redirect ke route Flask payment
      window.location.href = `/payment?city=${encodeURIComponent(this.selectedCity)}&ticket=${encodeURIComponent(ticket.type)}&price=${encodeURIComponent(ticket.price)}`;
    } else {
      alert('Please select a ticket type first.');
    }
  }

  getPrice(type){
    const prices = { "Standard":"Rp 450.000", "Premium":"Rp 850.000", "VIP":"Rp 1.250.000" };
    return prices[type];
  }
}

const bookingModal = new BookingModal("ticketModal","selectBtn");
