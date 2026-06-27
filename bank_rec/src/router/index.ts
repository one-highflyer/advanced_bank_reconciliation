import { createRouter, createWebHistory } from "vue-router";
import CashCodingPage from "@/pages/CashCodingPage.vue";
import MatchedPage from "@/pages/MatchedPage.vue";
import ReconcilePage from "@/pages/ReconcilePage.vue";
import RulesPage from "@/pages/RulesPage.vue";

export const router = createRouter({
  history: createWebHistory("/bank-rec"),
  routes: [
    {
      path: "/",
      redirect: "/reconcile",
    },
    {
      path: "/reconcile",
      name: "Reconcile",
      component: ReconcilePage,
    },
    {
      path: "/bank-coding",
      name: "Bank Coding",
      component: CashCodingPage,
    },
    {
      path: "/cash-coding",
      redirect: (to) => ({
        path: "/bank-coding",
        query: to.query,
        hash: to.hash,
      }),
    },
    {
      path: "/matched",
      name: "Matched",
      component: MatchedPage,
    },
    {
      path: "/rules",
      name: "Rules",
      component: RulesPage,
    },
  ],
});
