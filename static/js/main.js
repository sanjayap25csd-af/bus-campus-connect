/**
 * Bus Campus Connect - Core JavaScript Interactions
 * Smart Bus Request and Travel Planning for Hostel Students
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Travel Type & Proof Requirement Synchronization (Requirement 15)
  const travelTypeSelect = document.getElementById('travel_type');
  const proofContainer = document.getElementById('proof_upload_container');
  const proofInput = document.getElementById('travel_proof');
  const proofBadge = document.getElementById('proof_requirement_badge');
  const normalNote = document.getElementById('normal_travel_proof_note');

  if (travelTypeSelect && proofContainer) {
    function handleTravelTypeChange() {
      const selectedValue = travelTypeSelect.value;
      if (selectedValue === 'Booked Bus / Ticket') {
        proofContainer.style.display = 'block';
        if (normalNote) normalNote.style.display = 'none';
        if (proofInput) proofInput.required = true;
        if (proofBadge) {
          proofBadge.innerText = 'Mandatory Proof Upload';
          proofBadge.className = 'badge badge-danger';
        }
      } else if (selectedValue === 'Special Permission') {
        proofContainer.style.display = 'block';
        if (normalNote) normalNote.style.display = 'none';
        if (proofInput) proofInput.required = false;
        if (proofBadge) {
          proofBadge.innerText = 'Optional Permission Letter';
          proofBadge.className = 'badge badge-warning';
        }
      } else if (selectedValue === 'Normal Travel') {
        proofContainer.style.display = 'none';
        if (normalNote) normalNote.style.display = 'block';
        if (proofInput) {
          proofInput.required = false;
          proofInput.value = '';
        }
      } else {
        proofContainer.style.display = 'none';
        if (normalNote) normalNote.style.display = 'none';
        if (proofInput) {
          proofInput.required = false;
          proofInput.value = '';
        }
      }
    }

    travelTypeSelect.addEventListener('change', handleTravelTypeChange);
    // Trigger on load
    handleTravelTypeChange();
  }

  // 2. File Input Label Preview
  document.querySelectorAll('input[type="file"]').forEach(function (input) {
    input.addEventListener('change', function (e) {
      const fileName = e.target.files[0] ? e.target.files[0].name : '';
      const preview = input.closest('.form-group')?.querySelector('.file-preview-name');
      if (preview && fileName) {
        preview.textContent = 'Selected: ' + fileName;
        preview.style.display = 'block';
      }
    });
  });

  // 3. Mobile Sidebar Toggle
  const sidebarToggle = document.getElementById('sidebar_toggle');
  const sidebar = document.querySelector('.management-sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('open');
    });
  }

  // 4. Auto dismiss alerts after 6 seconds
  setTimeout(function () {
    document.querySelectorAll('.alert').forEach(function (alert) {
      alert.style.transition = 'opacity 0.5s ease';
      alert.style.opacity = '0';
      setTimeout(function () { alert.remove(); }, 500);
    });
  }, 6000);
});

// Modal Utilities
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('show');
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('show');
  }
}

// Close modal when clicking backdrop
document.addEventListener('click', function (e) {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('show');
  }
});

// Allocate Bus Modal Trigger
function openAllocateModal(requestId, studentReg, travelDate, timeStr) {
  const reqInput = document.getElementById('modal_allocate_request_id');
  const detailsSpan = document.getElementById('modal_allocate_details');
  if (reqInput) reqInput.value = requestId;
  if (detailsSpan) {
    detailsSpan.innerHTML = `<strong>Register No:</strong> <span class="table-reg-no">${studentReg}</span> &bull; <strong>Slot:</strong> ${travelDate} at ${timeStr}`;
  }
  openModal('allocateBusModal');
}

// Proof Inspection Modal Trigger
function openProofModal(requestId, proofUrl, studentReg, currentStatus) {
  const reqInput = document.getElementById('modal_proof_request_id');
  const proofContainer = document.getElementById('modal_proof_preview_container');
  const regSpan = document.getElementById('modal_proof_reg');
  
  if (reqInput) reqInput.value = requestId;
  if (regSpan) regSpan.innerText = studentReg;
  
  if (proofContainer) {
    if (!proofUrl || proofUrl.trim() === '') {
      proofContainer.innerHTML = '<p class="text-muted">No proof document uploaded for this request.</p>';
    } else {
      const isPdf = proofUrl.toLowerCase().endsWith('.pdf');
      if (isPdf) {
        proofContainer.innerHTML = `
          <div style="text-align: center; padding: 2rem;">
            <p style="margin-bottom: 1rem;">Document format: <strong>PDF Document</strong></p>
            <a href="${proofUrl}" target="_blank" class="btn btn-secondary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
              Open PDF Document in New Tab
            </a>
          </div>
        `;
      } else {
        proofContainer.innerHTML = `
          <div style="text-align: center;">
            <img src="${proofUrl}" alt="Proof Document" style="max-width: 100%; max-height: 400px; border-radius: 8px; border: 1px solid #e2e8f0; object-fit: contain;">
          </div>
        `;
      }
    }
  }
  openModal('verifyProofModal');
}

// Student College ID Modal Trigger
function openIdCardModal(userId, idCardUrl, studentName, studentReg, currentStatus) {
  const userInput = document.getElementById('modal_id_user_id');
  const detailsSpan = document.getElementById('modal_id_details');
  const previewContainer = document.getElementById('modal_id_preview');

  if (userInput) userInput.value = userId;
  const statusBadge = currentStatus === 'Verified'
    ? '<span class="badge badge-success">&check; Currently Verified</span>'
    : (currentStatus === 'Rejected' ? '<span class="badge badge-danger">&cross; Currently Rejected</span>' : '<span class="badge badge-warning">Currently Pending Review</span>');
  if (detailsSpan) detailsSpan.innerHTML = `<strong>${studentName}</strong> (<span class="table-reg-no">${studentReg}</span>) &bull; ${statusBadge}`;

  if (previewContainer) {
    if (!idCardUrl || idCardUrl.trim() === '') {
      previewContainer.innerHTML = '<p class="text-muted">No ID card uploaded.</p>';
    } else {
      const isPdf = idCardUrl.toLowerCase().endsWith('.pdf');
      if (isPdf) {
        previewContainer.innerHTML = `
          <div style="text-align: center; padding: 1.5rem;">
            <a href="${idCardUrl}" target="_blank" class="btn btn-secondary">
              View College ID Card (PDF)
            </a>
          </div>
        `;
      } else {
        previewContainer.innerHTML = `
          <div style="text-align: center;">
            <img src="${idCardUrl}" alt="College ID" style="max-width: 100%; max-height: 350px; border-radius: 8px; border: 1px solid #e2e8f0;">
          </div>
        `;
      }
    }
  }
  openModal('verifyIdModal');
}

