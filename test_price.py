from price_tracker import get_price

url = "https://www.amazon.es/Lotus-Style-Colección-Millennial-LS2169-2/dp/B08HM5L35D/ref=pd_day0fbt_d_sccl_1/262-3878971-0093029?pd_rd_w=AOhh1&content-id=amzn1.sym.7d8a3d0a-bcc2-4c07-91d5-30902c2587f5&pf_rd_p=7d8a3d0a-bcc2-4c07-91d5-30902c2587f5&pf_rd_r=Q3AM6W1187Q9QT9HDVGV&pd_rd_wg=U1UhT&pd_rd_r=8f33f310-92f7-44f9-85b9-843e040e93d9&pd_rd_i=B08HM5L35D&psc=1"
print(get_price(url))
