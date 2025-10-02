// static/script/user/homepage.js

class BookingModal {
    constructor(modalId, closeBtnId) {
        this.modal = document.getElementById(modalId);
        this.closeBtn = document.getElementById(closeBtnId);

        // Tutup modal kalau klik tombol close
        this.closeBtn.onclick = () => {
            this.close();
        };

        // Tutup modal kalau klik di luar modal-content
        window.onclick = (event) => {// static/script/user/homepage.js

class BookingModal {
    constructor(modalId) {
        this.modal = document.getElementById(modalId);
        this.closeBtn = this.modal.querySelector(".close"); // cari tombol close di dalam modal

        // Tutup modal kalau klik tombol close
        this.closeBtn.onclick = () => {
            this.close();
        };

        // Tutup modal kalau klik di luar modal-content
        window.onclick = (event) => {
            if (event.target === this.modal) {
                this.close();
            }
        };
    }

    open(city) {
        // Boleh tampilkan nama kota biar lebih dinamis
        const citySpan = this.modal.querySelector("#modalCity");
        if (citySpan) {
            citySpan.textContent = city;
        }

        this.modal.style.display = "block";
    }

    close() {
        this.modal.style.display = "none";
    }
}

// buat object global biar bisa dipanggil di onclick html
window.bookingModal = new BookingModal("ticketModal");

            if (event.target === this.modal) {
                this.close();
            }
        };
    }

    open(city) {
        // Boleh tampilkan nama kota biar lebih dinamis
        const citySpan = this.modal.querySelector("#modalCity");
        if (citySpan) {
            citySpan.textContent = city;
        }

        this.modal.style.display = "block";
    }

    close() {
        this.modal.style.display = "none";
    }
}

// buat object global biar bisa dipanggil di onclick html
window.bookingModal = new BookingModal("ticketModal", "selectBtn");
