"""
AHPMASTER Pricing Page - Standalone
요금제 및 PayPal 결제 전용 페이지
"""
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="AHPMASTER Pricing",
    page_icon="💳",
    layout="wide"
)

# Language detection
lang = st.query_params.get("lang", "ko")
if lang not in ["ko", "en"]:
    lang = "ko"

def _(ko, en):
    return en if lang == "en" else ko

st.title(_("💳 요금제", "💳 Pricing"))

# Pricing plans
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Basic")
    st.markdown("### 300,000원")
    st.caption(_("2개월", "2 months"))
    st.markdown("""
    - """ + _("표본 10개까지", "Up to 10 samples") + """
    - """ + _("기본 AHP 분석", "Basic AHP analysis") + """
    - """ + _("엑셀 다운로드", "Excel download") + """
    """)
    if st.button(_("결제 Basic", "Pay Basic"), key="pay_basic", use_container_width=True):
        st.info(_("로그인 후 결제 가능합니다.", "Please login to pay."))

with col2:
    st.subheader("Standard ⭐ BEST")
    st.markdown("### 500,000원")
    st.caption(_("2개월", "2 months"))
    st.markdown("""
    - """ + _("표본 무제한", "Unlimited samples") + """
    - """ + _("T-Test/ANOVA 포함", "Includes T-Test/ANOVA") + """
    - """ + _("기본 AHP 분석", "Basic AHP analysis") + """
    - """ + _("엑셀 다운로드", "Excel download") + """
    """)
    if st.button(_("결제 Standard", "Pay Standard"), key="pay_standard", use_container_width=True):
        st.info(_("로그인 후 결제 가능합니다.", "Please login to pay."))

with col3:
    st.subheader("Pro")
    st.markdown("### 950,000원")
    st.caption(_("2개월", "2 months"))
    st.markdown("""
    - """ + _("표본 무제한", "Unlimited samples") + """
    - """ + _("퍼지 AHP 포함", "Includes Fuzzy AHP") + """
    - """ + _("T-Test/ANOVA 포함", "Includes T-Test/ANOVA") + """
    - """ + _("우선 지원", "Priority support") + """
    """)
    if st.button(_("결제 Pro", "Pay Pro"), key="pay_pro", use_container_width=True):
        st.info(_("로그인 후 결제 가능합니다.", "Please login to pay."))

st.divider()

# PayPal section (English only)
if lang == "en":
    st.subheader("PayPal Payment")
    st.markdown(_("해외 결제는 PayPal을 이용하세요.", "For international payments, use PayPal."))
    
    # PayPal buttons will be rendered here
    # Note: Full PayPal integration requires Secrets configuration
    paypal_html = """
    <div id="paypal-button-container"></div>
    <script src="https://www.paypal.com/sdk/js?client-id=YOUR_CLIENT_ID&currency=USD"></script>
    <script>
        paypal.Buttons({
            createOrder: function(data, actions) {
                return actions.order.create({
                    purchase_units: [{
                        amount: { value: '330.00' }
                    }]
                });
            },
            onApprove: function(data, actions) {
                return actions.order.capture().then(function(details) {
                    alert('Payment completed by ' + details.payer.name.given_name);
                });
            }
        }).render('#paypal-button-container');
    </script>
    """
    components.html(paypal_html, height=300)

st.divider()
st.caption(_("문의: jeon080423@gmail.com", "Contact: jeon080423@gmail.com"))
