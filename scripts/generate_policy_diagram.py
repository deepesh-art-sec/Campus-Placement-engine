import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUT_DIR = r"C:\Users\Nitro-V\.gemini\antigravity\scratch\deviathon-placement-engine\docs\pdf_assets"
os.makedirs(OUT_DIR, exist_ok=True)

def create_policy_diagram():
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis('off')
    fig.patch.set_facecolor('#F8FAFC')

    ax.text(50, 46, "INSTITUTIONAL OFFER POLICY ENGINE & UPGRADE LADDER", ha='center', va='center', fontsize=9.5, fontweight='bold', color='#0F172A')

    # 3 Policy Columns
    # Policy 1: Strict One-Offer
    p1 = patches.FancyBboxPatch((4, 10), 28, 30, boxstyle="round,pad=0.5", ec="#EF4444", fc="#FEF2F2", lw=1.5)
    ax.add_patch(p1)
    ax.text(18, 36, "Policy 1: Strict One-Offer", ha='center', va='center', fontsize=7.5, fontweight='bold', color='#991B1B')
    ax.text(18, 25, "First Accepted Offer\n\nSTATUS: LOCKED\n(Barred from all future drives)", ha='center', va='center', fontsize=6.8, color='#7F1D1D', multialignment='center')
    ax.text(18, 14, "Unblocks: Only if revoked", ha='center', va='center', fontsize=6.2, fontstyle='italic', color='#B91C1C')

    # Policy 2: Progressive Multiplier
    p2 = patches.FancyBboxPatch((36, 10), 28, 30, boxstyle="round,pad=0.5", ec="#3B82F6", fc="#EFF6FF", lw=1.5)
    ax.add_patch(p2)
    ax.text(50, 36, "Policy 2: Progressive Multiplier", ha='center', va='center', fontsize=7.5, fontweight='bold', color='#1E40AF')
    ax.text(50, 25, "Current Offer: 6.0 LPA\nMultiplier: 1.5x (e.g.)\n\nREQUIRED: >= 9.0 LPA", ha='center', va='center', fontsize=6.8, color='#1E3A8A', multialignment='center')
    ax.text(50, 14, "Unblocks: Higher CTC tier", ha='center', va='center', fontsize=6.2, fontstyle='italic', color='#2563EB')

    # Policy 3: Tiered Quota (Dream)
    p3 = patches.FancyBboxPatch((68, 10), 28, 30, boxstyle="round,pad=0.5", ec="#10B981", fc="#ECFDF5", lw=1.5)
    ax.add_patch(p3)
    ax.text(82, 36, "Policy 3: Tiered Quotas", ha='center', va='center', fontsize=7.5, fontweight='bold', color='#065F46')
    ax.text(82, 25, "1 Standard (<= 8 LPA) +\n1 Dream (8-18 LPA) +\n1 Super-Dream (>= 18 LPA)", ha='center', va='center', fontsize=6.8, color='#047857', multialignment='center')
    ax.text(82, 14, "Unblocks: Unfilled tier quota", ha='center', va='center', fontsize=6.2, fontstyle='italic', color='#059669')

    # Bottom summary
    badge = patches.FancyBboxPatch((20, 2), 60, 5.5, boxstyle="round,pad=0.4", ec="#059669", fc="#10B981", lw=1.2)
    ax.add_patch(badge)
    ax.text(50, 4.8, "DYNAMIC REPLAY: ATOMIC RE-CALCULATION ACROSS ALL CANDIDATES IN REAL-TIME", ha='center', va='center', fontsize=6.8, fontweight='bold', color='#FFFFFF')

    plt.tight_layout()
    out_file = os.path.join(OUT_DIR, "diagram5_policy.png")
    plt.savefig(out_file, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print("Saved:", out_file)

if __name__ == "__main__":
    create_policy_diagram()
