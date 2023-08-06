import joblib , random
import pandas as pd
from flask import Flask, jsonify
from flask_restful import Resource, Api
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
api = Api(app)

# Load data and similarity matrices
product_data_1 = joblib.load("product_data_1.pkl")
product_data_2 = joblib.load("product_data_2.pkl")
data_1_similarity = joblib.load("data_1_similarity.pkl")
data_2_similarity = joblib.load("data_2_similarity.pkl")

# Load cart and wishlist data
data = joblib.load("data.pkl")
similarity_matrix = joblib.load("similarity_matrix.pkl")
product_features = joblib.load('product_features.pkl')
encoded_features = pd.get_dummies(product_features[['category_name', 'sub_category_name']])

                                                                                    #Similarity(common)
class Similarity(Resource):
    def get(self, prod_id):
        if prod_id in product_data_1['id'].values:
            sim_scores = list(enumerate(data_1_similarity[prod_id]))
            sorted_sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            similar_product_indices = [i[0] for i in sorted_sim_scores[1:11]]
            df_similar = product_data_1.loc[similar_product_indices]
        elif prod_id in product_data_2['id'].values:
            sim_scores = list(enumerate(data_2_similarity[prod_id]))
            sorted_sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            similar_product_indices = [i[0] for i in sorted_sim_scores[1:11]]
            df_similar = product_data_2.loc[similar_product_indices]
        else:
            return jsonify({
                "status": "error",
                "response_code": 404,
                "message": "Product not found"
            })

        similar_products = df_similar["id"].tolist()
        return jsonify({
            "status": "success",
            "response_code": 200,
            "data": {
                "product_ids": similar_products
            }
        })
                                                                                        #cart 
    
class CartRecommendation(Resource):
    def get(self, variant_id):
        recommendations = self.cart_product_recommendation([variant_id])
        return {'recommendations': [int(x) for x in recommendations]}


    def cart_product_recommendation(self,cart_products, n=5):
        cart_indices = []
        for product in cart_products:
            try:
                index = data[data['id'] == product].index[0]
                cart_indices.append(index)
            except IndexError:
                raise ValueError (f"{product} is not in the product database.")

        cart_similarities = similarity_matrix[cart_indices].sum(axis=0)
        similar_indices = cart_similarities.argsort()[::-1]

        recommended_products = []
        for i in similar_indices:
            product_id = data.loc[i, 'id']
            if product_id not in cart_products:
                recommended_products.append(product_id)
            if len(recommended_products) == n:
                break
        return recommended_products
                                                                                        #wishlist

class WishlistRecommendation(Resource):
    def get(self, variant_id):
        recommendations = self.wishlist_product_recommendation([variant_id])
        return {'recommendations': recommendations}

    def wishlist_product_recommendation(self,variant_ids):
        recommendations = []
        for variant_id in variant_ids:
            product_indices = product_features[product_features['variant_id'] == variant_id].index.tolist()
            if len(product_indices) == 0:
                raise ValueError ("Product with variant ID {} not found in the database.".format(variant_id))
            else:
                product_idx = product_indices[0]
                sim_scores = list(enumerate(cosine_similarity(encoded_features, encoded_features)))
                sim_scores = sorted(sim_scores, key=lambda x: x[1][product_idx], reverse=True)
                sim_scores = sim_scores[2:4]
                product_indices = [i[0] for i in sim_scores if i[0] != product_idx]
                recommendations.extend(product_features.loc[product_indices, 'variant_id'].tolist())
        return recommendations
     
                                                                                #Recommendations(cart & wishlist)                                               
class ProductRecommendation(Resource):
    def get(self, product_id):
        cart_recommendations = self.get_cart_recommendations(product_id)
        wishlist_recommendations = self.get_wishlist_recommendations(product_id)
        return {
            "cart_recommendations": [int(x) for x in cart_recommendations],
            "wishlist_recommendations": wishlist_recommendations
        }

    def get_cart_recommendations(self, variant_id, n=5):
        cart_indices = []
        try:
            index = data[data['id'] == variant_id].index[0]
            cart_indices.append(index)
        except IndexError:
            return []

        cart_similarities = similarity_matrix[cart_indices].sum(axis=0)
        similar_indices = cart_similarities.argsort()[::-1]

        recommended_products = []
        for i in similar_indices:
            recommended_product_id = data.loc[i, 'id']
            if recommended_product_id != variant_id:
                recommended_products.append(recommended_product_id)
            if len(recommended_products) == n:
                break

        return recommended_products
     

    def get_wishlist_recommendations(self, variant_id, n=5):
        product_indices = product_features[product_features['variant_id'] == variant_id].index.tolist()
        if len(product_indices) == 0:
            return []
        else:
            product_idx = product_indices[0]
            sim_scores = list(enumerate(cosine_similarity(encoded_features, encoded_features)))
            sim_scores = sorted(sim_scores, key=lambda x: x[1][product_idx], reverse=True)
            sim_scores = sim_scores[2:4]
            product_indices = [i[0] for i in sim_scores if i[0] != product_idx]
            recommended_products = product_features.loc[product_indices, 'variant_id'].tolist()[:n]
            return recommended_products
          
        
                                                                               # combine cart-data and wishlist-data into single list
class Combined(Resource):
    def get(self, product_id):
        cart_recommendations = self.get_cart_recommendations(product_id)
        wishlist_recommendations = self.get_wishlist_recommendations(product_id)

        # Combine cart and wishlist into a single list
        all_recommendations = cart_recommendations + wishlist_recommendations

        return {
            "recommendations": [int(x) for x in all_recommendations]
        }

    def get_cart_recommendations(self, product_id, n=5):
        cart_indices = []
        try:
            index = data[data['id'] == product_id].index[0]
            cart_indices.append(index)
        except IndexError:
            return []

        cart_similarities = similarity_matrix[cart_indices].sum(axis=0)
        similar_indices = cart_similarities.argsort()[::-1]

        recommended_products = []
        for i in similar_indices:
            recommended_product_id = data.loc[i, 'id']
            if recommended_product_id != product_id:
                recommended_products.append(recommended_product_id)
            if len(recommended_products) == n:
                break

        return recommended_products
       
    def get_wishlist_recommendations(self, variant_id, n=5):
        product_indices = product_features[product_features['variant_id'] == variant_id].index.tolist()
        if len(product_indices) == 0:
            return []
        else:
            product_idx = product_indices[0]
            sim_scores = list(enumerate(cosine_similarity(encoded_features, encoded_features)))
            sim_scores = sorted(sim_scores, key=lambda x: x[1][product_idx], reverse=True)
            sim_scores = sim_scores[2:4]
            product_indices = [i[0] for i in sim_scores if i[0] != product_idx]
            recommended_products = product_features.loc[product_indices, 'variant_id'].tolist()[:n]
            return recommended_products
        
        
                                                                                        #priority-wise
class Recommendations(Resource):
    
    def get(self, variant_id,n = 5):
        wishlist_recommendations = self.get_wishlist_recommendations(variant_id, n)
        cart_wishlist_recommendations = self.get_cart_wishlist_recommendations(variant_id, n)
        recommendations = wishlist_recommendations + cart_wishlist_recommendations
        random.shuffle(recommendations)
        recommendations = [int(recommendation) for recommendation in recommendations]     
        return recommendations[:n]

    def get_wishlist_recommendations(self, variant_id, n=5):
        product_indices = product_features[product_features['variant_id'] == variant_id].index.tolist()
        if len(product_indices) == 0:
            return []
        else:
            product_idx = product_indices[0]
            sim_scores = list(enumerate(cosine_similarity(encoded_features, encoded_features)))
            sim_scores = sorted(sim_scores, key=lambda x: x[1][product_idx], reverse=True)
            sim_scores = sim_scores[2:4]
            product_indices = [i[0] for i in sim_scores if i[0] != product_idx]
            recommended_products = product_features.loc[product_indices, 'variant_id'].tolist()[:n]
            return recommended_products
        
        
    def get_cart_wishlist_recommendations(self, variant_id, n=5):
        cart_indices = []
        try:
            index = data[data['id'] == variant_id].index[0]
            cart_indices.append(index)
        except IndexError:
            return []

        cart_similarities = similarity_matrix[cart_indices].sum(axis=0)
        similar_indices = cart_similarities.argsort()[::-1]

        recommended_products = []
        for i in similar_indices:
            recommended_product_id = data.loc[i, 'id']
            if recommended_product_id != variant_id:
                recommended_products.append(recommended_product_id)
            if len(recommended_products) == n:
                break

        wishlist_recommendations = self.get_wishlist_recommendations(variant_id, n)
        final_recommendations = []

        # Add same products from cart and wishlist first
        same_products = list(set(recommended_products) & set(wishlist_recommendations))
        final_recommendations.extend(same_products)

        # Add cart-only recommendations
        cart_only_products = list(set(recommended_products) - set(same_products))
        final_recommendations.extend(cart_only_products)

        # Add random similar product recommendations
        random_products = list(set(recommended_products + wishlist_recommendations) - set(final_recommendations))
        random.shuffle(random_products)
        final_recommendations.extend(random_products)

        return final_recommendations[:n]
    
    
api.add_resource(Similarity, '/similar/<int:prod_id>')
api.add_resource(CartRecommendation, '/cart/<int:variant_id>')
api.add_resource(WishlistRecommendation, '/wishlist/<int:variant_id>')
api.add_resource(ProductRecommendation, '/cart_wishlist/<int:variant_id>')
api.add_resource(Combined, '/combined/<int:variant_id>')
api.add_resource(Recommendations, '/recommendations/<int:variant_id>')

if __name__ == '__main__':
    app.run(debug=True)    