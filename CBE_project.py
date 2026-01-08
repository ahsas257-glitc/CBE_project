import streamlit as st

def load_css(path="theme/styles.css"):
    with open(path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def page_home():
    load_css()

    # Header (logos + title)
    c1, c2, c3 = st.columns([1, 3, 1], vertical_alignment="center")
    with c1:
        st.image("theme/assets/logo/unicef.png", width=110)
    with c2:
        st.markdown(
            """
            <div class="glass" style="position: relative; text-align:center;">
              <div style="font-size:34px; font-weight:800; letter-spacing:0.2px;">
                Welcome to CBE Monitoring Dashboard
              </div>
              <div class="small-muted" style="margin-top:6px; font-size:14px;">
                Light • Liquid Glass • Animated UI
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        st.image("theme/assets/logo/ppc.png", width=110)

    st.write("")  # spacing

    # Intro card
    st.markdown(
        """
        <div class="glass" style="position: relative;">
          <div style="font-size:16px; line-height:1.7;">
            This dashboard has been developed for <b>UNICEF’s Community-Based Education (CBE)</b> project.<br>
            <b>PPC</b>, as the <b>Third Party Monitoring (TPM)</b> partner, is responsible for collecting, validating,
            and reporting monitoring data from the field.
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    # Objectives + Features (3 cards)
    left, right = st.columns([2, 3], gap="large")

    with left:
        st.markdown(
            """
            <div class="glass" style="position: relative;">
              <div style="font-size:18px; font-weight:750; margin-bottom:10px;">🎯 Project Objectives</div>
              <ul style="margin:0; padding-left:18px; line-height:1.8;">
                <li>Improve access to education in remote areas</li>
                <li>Ensure quality learning environment for CBE classes</li>
                <li>Monitor teacher performance and student attendance</li>
                <li>Provide transparent data for decision-making</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    with right:
        st.markdown(
            """
            <div class="glass" style="position: relative;">
              <div style="font-size:18px; font-weight:750; margin-bottom:10px;">🛠️ Dashboard Features</div>
              <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:12px;">
                <div class="glass" style="position:relative; padding:14px; border-radius:18px;">
                  <div style="font-weight:700;">📥 Upload</div>
                  <div class="small-muted" style="margin-top:6px;">Upload and validate survey data</div>
                </div>
                <div class="glass" style="position:relative; padding:14px; border-radius:18px;">
                  <div style="font-weight:700;">📊 Tracking</div>
                  <div class="small-muted" style="margin-top:6px;">Track monitoring results (QC_Log)</div>
                </div>
                <div class="glass" style="position:relative; padding:14px; border-radius:18px;">
                  <div style="font-weight:700;">📑 Export</div>
                  <div class="small-muted" style="margin-top:6px;">Export reports for analysis</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
