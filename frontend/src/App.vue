<template>
  <div class="app">
    <nav class="app-nav">
      <span class="brand">PaperMind</span>

      <div class="nav-links">
        <RouterLink to="/">上传文献</RouterLink>
        <RouterLink to="/library">我的文献</RouterLink>
      </div>
    </nav>

    <RouterView />
  </div>
</template>

<style scoped>
.app-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 28px;
  border-bottom: 1px solid #e2e8f0;
  background: white;
}

.brand {
  font-size: 18px;
  font-weight: 700;
}

.nav-links {
  display: flex;
  gap: 20px;
}

.nav-links a {
  color: #64748b;
  text-decoration: none;
}

.nav-links a.router-link-active {
  color: #2563eb;
  font-weight: 600;
}

@media (max-width: 480px) {
  .app-nav {
    padding: 14px 16px;
  }

  .nav-links {
    gap: 12px;
  }
}
</style>
